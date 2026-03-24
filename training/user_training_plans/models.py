import uuid
from sqlalchemy import Column, DateTime, Date, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from training.db import Base


class UserTrainingPlan(Base):
    """
    User-specific training plan instance. current_version_id is nullable for bootstrap.
    """

    __tablename__ = "user_training_plans"

    user_plan_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)
    template_id = Column(UUID(as_uuid=True), ForeignKey("training_plan_templates.template_id"), nullable=False)
    current_version_id = Column(UUID(as_uuid=True), ForeignKey("training_plan_versions.version_id"), nullable=True)
    start_date = Column(Date, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
