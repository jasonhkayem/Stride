import uuid

from sqlalchemy import Column, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import relationship

from training.db import Base


class TrainingPlanAdjustment(Base):
    """
    Suggested or approved modifications to a user training plan.
    """

    __tablename__ = "training_plan_adjustments"

    adjustment_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_training_plan_id = Column(UUID(as_uuid=True), ForeignKey("user_training_plans.user_plan_id"), nullable=False)
    session_id = Column(UUID(as_uuid=True), ForeignKey("chatbot_sessions.chatbot_id"), nullable=False)
    previous_version_id = Column(UUID(as_uuid=True), ForeignKey("training_plan_versions.version_id"), nullable=False)
    new_version_id = Column(UUID(as_uuid=True), ForeignKey("training_plan_versions.version_id"), nullable=True)
    suggested_changes = Column(JSON, nullable=False)
    validated_changes = Column(JSON, nullable=True)
    status = Column(String(20), nullable=False, default="suggested", server_default="suggested")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user_training_plan = relationship("UserTrainingPlan", foreign_keys=[user_training_plan_id])
    chatbot_session = relationship("ChatbotSession", foreign_keys=[session_id])
    previous_version = relationship("TrainingPlanVersion", foreign_keys=[previous_version_id])
    new_version = relationship("TrainingPlanVersion", foreign_keys=[new_version_id])
