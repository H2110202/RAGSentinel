from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), index=True, nullable=False)
    email = Column(String(100), index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(100))
    role = Column(String(20), default="user")
    is_active = Column(Boolean, default=True)
    is_department_admin = Column(Boolean, default=False)
    dingtalk_userid = Column(String(64), nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    departments = relationship("Department", secondary="user_departments", back_populates="members")
