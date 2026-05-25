from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base


class KnowledgeBase(Base):
    __tablename__ = "knowledge_bases"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    is_public = Column(Boolean, default=False)
    ragflow_dataset_id = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    documents = relationship("Document", back_populates="knowledge_base")
    permissions = relationship("KBPermission", back_populates="knowledge_base")
    creator = relationship("User", foreign_keys=[created_by])


class Document(Base):
    __tablename__ = "documents"
    id = Column(Integer, primary_key=True, index=True)
    kb_id = Column(Integer, ForeignKey("knowledge_bases.id"), nullable=False)
    title = Column(String(500), nullable=False)
    file_path = Column(String(500), nullable=True)
    file_type = Column(String(50), nullable=True)
    file_size = Column(Integer, default=0)
    uploaded_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    status = Column(String(20), default="pending")
    ragflow_document_id = Column(String(100), nullable=True)
    chunk_num = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    knowledge_base = relationship("KnowledgeBase", back_populates="documents")
    uploader = relationship("User", foreign_keys=[uploaded_by])
    approval_instance = relationship("ApprovalInstance", back_populates="document", uselist=False)
    doc_permissions = relationship("DocumentPermission", back_populates="document", cascade="all, delete-orphan")


class DocumentPermission(Base):
    __tablename__ = "document_permissions"
    id = Column(Integer, primary_key=True, index=True)
    doc_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    target_type = Column(String(20), nullable=False)
    target_id = Column(Integer, nullable=True)
    permission_level = Column(String(20), default="view")
    created_at = Column(DateTime, default=datetime.utcnow)
    document = relationship("Document", back_populates="doc_permissions")


class KBPermission(Base):
    __tablename__ = "kb_permissions"
    id = Column(Integer, primary_key=True, index=True)
    kb_id = Column(Integer, ForeignKey("knowledge_bases.id"), nullable=False)
    target_type = Column(String(20), nullable=False)
    target_id = Column(Integer, nullable=True)
    permission_level = Column(String(20), default="view")
    created_at = Column(DateTime, default=datetime.utcnow)
    knowledge_base = relationship("KnowledgeBase", back_populates="permissions")


class ProjectGroup(Base):
    __tablename__ = "project_groups"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    members = relationship("ProjectGroupMember", back_populates="group")
    creator = relationship("User", foreign_keys=[created_by])


class ProjectGroupMember(Base):
    __tablename__ = "project_group_members"
    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(Integer, ForeignKey("project_groups.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    role = Column(String(20), default="member")
    created_at = Column(DateTime, default=datetime.utcnow)
    group = relationship("ProjectGroup", back_populates="members")
    user = relationship("User")


class ApprovalChain(Base):
    __tablename__ = "approval_chains"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    steps_config = Column(Text, nullable=False)
    is_active = Column(Boolean, default=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    creator = relationship("User", foreign_keys=[created_by])


class ApprovalInstance(Base):
    __tablename__ = "approval_instances"
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    chain_id = Column(Integer, ForeignKey("approval_chains.id"), nullable=True)
    current_step = Column(Integer, default=0)
    status = Column(String(20), default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    document = relationship("Document", back_populates="approval_instance")
    chain = relationship("ApprovalChain", foreign_keys=[chain_id])
    steps = relationship("ApprovalStep", back_populates="instance")


class ApprovalStep(Base):
    __tablename__ = "approval_steps"
    id = Column(Integer, primary_key=True, index=True)
    instance_id = Column(Integer, ForeignKey("approval_instances.id"), nullable=False)
    step_order = Column(Integer, nullable=False)
    approver_type = Column(String(30), nullable=False)
    approver_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    status = Column(String(20), default="pending")
    comment = Column(Text, nullable=True)
    approved_at = Column(DateTime, nullable=True)
    instance = relationship("ApprovalInstance", back_populates="steps")
    approver = relationship("User", foreign_keys=[approver_id])