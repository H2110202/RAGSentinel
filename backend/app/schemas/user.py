from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class UserBase(BaseModel):
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None

class UserCreate(UserBase):
    password: str
    role: str = "user"

class UserUpdate(BaseModel):
    email: Optional[str] = None
    full_name: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None
    is_department_admin: Optional[bool] = None

class UserResponse(UserBase):
    id: int
    role: str
    is_active: bool
    is_department_admin: bool
    dingtalk_userid: Optional[str] = None
    created_at: datetime
    department_ids: List[int] = []
    department_names: List[str] = []
    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

def user_to_response(user) -> dict:
    dept_ids = [d.id for d in user.departments]
    dept_names = [d.name for d in user.departments]
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role,
        "is_active": user.is_active,
        "is_department_admin": user.is_department_admin,
        "dingtalk_userid": user.dingtalk_userid,
        "created_at": user.created_at,
        "department_ids": dept_ids,
        "department_names": dept_names,
    }
