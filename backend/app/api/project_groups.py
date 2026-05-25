from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional, List
from pydantic import BaseModel
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.knowledge import ProjectGroup, ProjectGroupMember

router = APIRouter()


class GroupCreate(BaseModel):
    name: str
    description: Optional[str] = None
    member_ids: List[int] = []


class GroupUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class GroupMembersUpdate(BaseModel):
    member_ids: List[int] = []


@router.get("/")
def list_groups(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    groups = db.query(ProjectGroup).filter(ProjectGroup.is_active == True).all()
    result = []
    for g in groups:
        members = db.query(ProjectGroupMember).filter(ProjectGroupMember.group_id == g.id).all()
        result.append({
            "id": g.id,
            "name": g.name,
            "description": g.description,
            "member_count": len(members),
            "members": [{
                "id": m.user.id,
                "full_name": m.user.full_name,
                "role": m.role,
            } for m in members],
            "created_at": g.created_at.isoformat() if g.created_at else None,
        })
    return result


@router.post("/")
def create_group(group: GroupCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="需要管理员权限")
    new_group = ProjectGroup(
        name=group.name,
        description=group.description,
        created_by=current_user.id,
    )
    db.add(new_group)
    db.flush()
    for uid in group.member_ids:
        member = ProjectGroupMember(
            group_id=new_group.id,
            user_id=uid,
            role="member",
        )
        db.add(member)
    db.commit()
    return {"id": new_group.id, "name": new_group.name, "message": "项目组创建成功"}


@router.put("/{group_id}")
def update_group(group_id: int, group_update: GroupUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="需要管理员权限")
    group = db.query(ProjectGroup).filter(ProjectGroup.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="项目组不存在")
    for key, value in group_update.model_dump(exclude_unset=True).items():
        setattr(group, key, value)
    db.commit()
    return {"message": "项目组更新成功"}


@router.put("/{group_id}/members")
def update_group_members(group_id: int, members_update: GroupMembersUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="需要管理员权限")
    group = db.query(ProjectGroup).filter(ProjectGroup.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="项目组不存在")
    db.query(ProjectGroupMember).filter(ProjectGroupMember.group_id == group_id).delete()
    for uid in members_update.member_ids:
        member = ProjectGroupMember(
            group_id=group_id,
            user_id=uid,
            role="member",
        )
        db.add(member)
    db.commit()
    return {"message": "成员更新成功"}


@router.delete("/{group_id}")
def delete_group(group_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="需要管理员权限")
    group = db.query(ProjectGroup).filter(ProjectGroup.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="项目组不存在")
    group.is_active = False
    db.commit()
    return {"message": "项目组已删除"}
