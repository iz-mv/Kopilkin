from datetime import datetime

from sqlalchemy import Column, String, Float, DateTime

from app.database import Base


class SavingsGoal(Base):
    __tablename__ = "savings_goals"

    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, index=True, nullable=False)

    title = Column(String, nullable=False)
    target_amount = Column(Float, nullable=False)
    current_amount = Column(Float, default=0.0)

    created_at = Column(DateTime, default=datetime.utcnow)