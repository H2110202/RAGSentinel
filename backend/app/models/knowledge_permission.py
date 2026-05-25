from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from datetime import datetime
from app.core.database import Base

class KnowledgePermission(Base):
    __tablename__ = "knowledge_permissions"
    id = Column(Integer, primary_key=True, index=True)
    knowledge_id = Column(String(100), nullable=False, index=True)
    knowledge_name = Column(String(255))
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    permission_type = Column(String(20), default="read")
    granted_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
