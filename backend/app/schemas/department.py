from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class DepartmentBase(BaseModel):
    name: str
    code: Optional[str] = None
    parent_id: Optional[int] = None

class DepartmentCreate(DepartmentBase):
    manager_id: Optional[int] = None

class DepartmentUpdate(BaseModel):
    name: Optional[str] = None
    manager_id: Optional[int] = None
    is_active: Optional[bool] = None

class DepartmentResponse(DepartmentBase):
    id: int
    dingtalk_id: Optional[str] = None
    manager_id: Optional[int] = None
    is_active: bool
    created_at: datetime
    class Config:
        from_attributes = True

class DepartmentTreeNode(BaseModel):
    id: int
    name: str
    code: Optional[str] = None
    dingtalk_id: Optional[str] = None
    parent_id: Optional[int] = None
    is_active: bool
    member_count: int
    children: List["DepartmentTreeNode"] = []

    class Config:
        from_attributes = True
