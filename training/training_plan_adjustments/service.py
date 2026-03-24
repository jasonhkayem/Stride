from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List, Optional
import uuid

from sqlalchemy import func, select

from training.db import SessionLocal
from training.training_plan_versions.models import TrainingPlanVersion
from training.user_training_plans.models import UserTrainingPlan

from .models import TrainingPlanAdjustment


class TrainingPlanAdjustmentNotFoundError(Exception):
    """Raised when an adjustment is not found."""


class TrainingPlanAdjustmentValidationError(Exception):
    """Raised when AI suggested changes are invalid."""


class TrainingPlanAdjustmentService:
    """CRUD + AI suggestion validation/application for training plan adjustments."""

    VALID_STATUSES = {"suggested", "approved", "rejected", "applied"}
    VALID_OPS = {"add", "replace", "remove"}

    @staticmethod
    def _to_uuid(value: str, field_name: str) -> uuid.UUID:
        try:
            return uuid.UUID(str(value))
        except (ValueError, TypeError) as exc:
            raise TrainingPlanAdjustmentValidationError(
                f"{field_name} must be a valid UUID"
            ) from exc

    @staticmethod
    def _normalize_path(path: Any) -> List[str]:
        if isinstance(path, str):
            return [p for p in path.strip("/").split("/") if p]
        if isinstance(path, list) and all(isinstance(p, (str, int)) for p in path):
            return [str(p) for p in path]
        raise TrainingPlanAdjustmentValidationError("operation path must be string or list")

    def validate_suggested_changes(self, suggested_changes: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(suggested_changes, dict):
            raise TrainingPlanAdjustmentValidationError("suggested_changes must be an object")

        operations = suggested_changes.get("operations")
        if operations is None:
            return {"operations": [], "merge_patch": suggested_changes}

        if not isinstance(operations, list):
            raise TrainingPlanAdjustmentValidationError("suggested_changes.operations must be a list")

        normalized_ops = []
        for index, operation in enumerate(operations, start=1):
            if not isinstance(operation, dict):
                raise TrainingPlanAdjustmentValidationError(
                    f"operation at index {index} must be an object"
                )
            op_type = operation.get("op")
            if op_type not in self.VALID_OPS:
                raise TrainingPlanAdjustmentValidationError(
                    f"operation at index {index} has invalid op '{op_type}'"
                )

            path = self._normalize_path(operation.get("path"))
            normalized = {"op": op_type, "path": path}
            if op_type in {"add", "replace"}:
                if "value" not in operation:
                    raise TrainingPlanAdjustmentValidationError(
                        f"operation at index {index} requires 'value'"
                    )
                normalized["value"] = operation.get("value")

            normalized_ops.append(normalized)

        return {"operations": normalized_ops, "merge_patch": suggested_changes.get("merge_patch")}

    def _assign_path(self, snapshot: Dict[str, Any], path: List[str], value: Any) -> None:
        cursor: Any = snapshot
        for key in path[:-1]:
            if isinstance(cursor, dict):
                cursor = cursor.setdefault(key, {})
            elif isinstance(cursor, list):
                idx = int(key)
                while len(cursor) <= idx:
                    cursor.append({})
                cursor = cursor[idx]
            else:
                raise TrainingPlanAdjustmentValidationError("invalid path target in snapshot")

        final_key = path[-1]
        if isinstance(cursor, dict):
            cursor[final_key] = value
            return

        if isinstance(cursor, list):
            idx = int(final_key)
            while len(cursor) <= idx:
                cursor.append(None)
            cursor[idx] = value
            return

        raise TrainingPlanAdjustmentValidationError("invalid final path target in snapshot")

    def _remove_path(self, snapshot: Dict[str, Any], path: List[str]) -> None:
        cursor: Any = snapshot
        for key in path[:-1]:
            if isinstance(cursor, dict):
                cursor = cursor.get(key)
            elif isinstance(cursor, list):
                cursor = cursor[int(key)] if int(key) < len(cursor) else None
            else:
                cursor = None
            if cursor is None:
                return

        final_key = path[-1]
        if isinstance(cursor, dict):
            cursor.pop(final_key, None)
        elif isinstance(cursor, list):
            idx = int(final_key)
            if 0 <= idx < len(cursor):
                cursor.pop(idx)

    def _merge_patch(self, target: Dict[str, Any], patch: Dict[str, Any]) -> Dict[str, Any]:
        result = deepcopy(target)
        for key, value in patch.items():
            if isinstance(value, dict) and isinstance(result.get(key), dict):
                result[key] = self._merge_patch(result[key], value)
            else:
                result[key] = value
        return result

    def _apply_operations(self, snapshot: Dict[str, Any], operations: List[Dict[str, Any]]) -> Dict[str, Any]:
        output = deepcopy(snapshot)
        for operation in operations:
            op_type = operation["op"]
            path = operation["path"]
            if op_type in {"add", "replace"}:
                self._assign_path(output, path, operation.get("value"))
            elif op_type == "remove":
                self._remove_path(output, path)
        return output

    def _create_new_version(
        self,
        session,
        user_training_plan_id: uuid.UUID,
        previous_version: TrainingPlanVersion,
        validated_changes: Dict[str, Any],
    ) -> TrainingPlanVersion:
        base_snapshot = deepcopy(previous_version.plan_snapshot or {})
        operations = validated_changes.get("operations", [])
        merge_patch = validated_changes.get("merge_patch")

        next_snapshot = self._apply_operations(base_snapshot, operations)
        if isinstance(merge_patch, dict) and merge_patch:
            next_snapshot = self._merge_patch(next_snapshot, merge_patch)

        max_version_stmt = select(func.max(TrainingPlanVersion.version_number)).where(
            TrainingPlanVersion.user_plan_id == user_training_plan_id
        )
        max_version = session.execute(max_version_stmt).scalar() or 0

        new_version = TrainingPlanVersion(
            user_plan_id=user_training_plan_id,
            version_number=int(max_version) + 1,
            plan_snapshot=next_snapshot,
            created_by="ai",
            change_summary="Applied AI training plan adjustment",
        )
        session.add(new_version)
        session.flush()

        user_plan = session.get(UserTrainingPlan, user_training_plan_id)
        if user_plan is not None:
            user_plan.current_version_id = new_version.version_id

        return new_version

    def _load_previous_version(self, session, previous_version_id: uuid.UUID) -> TrainingPlanVersion:
        previous_version = session.get(TrainingPlanVersion, previous_version_id)
        if previous_version is None:
            raise TrainingPlanAdjustmentValidationError("previous_version_id not found")
        return previous_version

    def create(self, payload: Dict[str, Any]) -> TrainingPlanAdjustment:
        with SessionLocal() as session:
            data = dict(payload)
            status = str(data.get("status", "suggested")).lower()
            if status not in self.VALID_STATUSES:
                raise TrainingPlanAdjustmentValidationError("status is invalid")

            validated_changes = self.validate_suggested_changes(data.get("suggested_changes", {}))
            data["validated_changes"] = validated_changes
            data["status"] = status

            previous_version_id = self._to_uuid(data["previous_version_id"], "previous_version_id")
            user_training_plan_id = self._to_uuid(
                data["user_training_plan_id"], "user_training_plan_id"
            )
            self._load_previous_version(session, previous_version_id)

            item = TrainingPlanAdjustment(**data)
            session.add(item)
            session.flush()

            if status in {"approved", "applied"}:
                previous_version = self._load_previous_version(session, previous_version_id)
                new_version = self._create_new_version(
                    session=session,
                    user_training_plan_id=user_training_plan_id,
                    previous_version=previous_version,
                    validated_changes=validated_changes,
                )
                item.new_version_id = new_version.version_id
                item.status = "applied"

            session.commit()
            session.refresh(item)
            return item

    def get_by_id(self, adjustment_id: str) -> Optional[TrainingPlanAdjustment]:
        with SessionLocal() as session:
            stmt = select(TrainingPlanAdjustment).where(
                TrainingPlanAdjustment.adjustment_id
                == self._to_uuid(adjustment_id, "adjustment_id")
            )
            return session.execute(stmt).scalar_one_or_none()

    def list_all(self) -> List[TrainingPlanAdjustment]:
        with SessionLocal() as session:
            stmt = select(TrainingPlanAdjustment).order_by(
                TrainingPlanAdjustment.created_at.desc()
            )
            return list(session.execute(stmt).scalars().all())

    def update(self, adjustment_id: str, payload: Dict[str, Any]) -> TrainingPlanAdjustment:
        with SessionLocal() as session:
            adjustment_uuid = self._to_uuid(adjustment_id, "adjustment_id")
            stmt = select(TrainingPlanAdjustment).where(
                TrainingPlanAdjustment.adjustment_id == adjustment_uuid
            )
            item = session.execute(stmt).scalar_one_or_none()
            if item is None:
                raise TrainingPlanAdjustmentNotFoundError("training_plan_adjustment not found")

            data = dict(payload)

            if "suggested_changes" in data:
                item.validated_changes = self.validate_suggested_changes(data["suggested_changes"])

            for key, value in data.items():
                if key == "suggested_changes":
                    item.suggested_changes = value
                elif key != "validated_changes":
                    setattr(item, key, value)

            requested_status = str(data.get("status", item.status)).lower()
            if requested_status not in self.VALID_STATUSES:
                raise TrainingPlanAdjustmentValidationError("status is invalid")
            item.status = requested_status

            should_apply = requested_status in {"approved", "applied"} and item.new_version_id is None
            if should_apply:
                previous_version = self._load_previous_version(session, item.previous_version_id)
                validated_changes = item.validated_changes or self.validate_suggested_changes(
                    item.suggested_changes
                )
                new_version = self._create_new_version(
                    session=session,
                    user_training_plan_id=item.user_training_plan_id,
                    previous_version=previous_version,
                    validated_changes=validated_changes,
                )
                item.new_version_id = new_version.version_id
                item.status = "applied"

            session.commit()
            session.refresh(item)
            return item

    def delete(self, adjustment_id: str) -> bool:
        with SessionLocal() as session:
            stmt = select(TrainingPlanAdjustment).where(
                TrainingPlanAdjustment.adjustment_id
                == self._to_uuid(adjustment_id, "adjustment_id")
            )
            item = session.execute(stmt).scalar_one_or_none()
            if item is None:
                raise TrainingPlanAdjustmentNotFoundError("training_plan_adjustment not found")

            session.delete(item)
            session.commit()
            return True
