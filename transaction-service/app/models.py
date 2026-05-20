from datetime import datetime

from sqlalchemy import Column, String, Float, DateTime

from app.database import Base


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, index=True, nullable=False)

    amount = Column(Float, nullable=False)
    category = Column(String, nullable=False)
    type = Column(String, nullable=False)  # income or expense
    description = Column(String, nullable=True)
    date = Column(String, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)