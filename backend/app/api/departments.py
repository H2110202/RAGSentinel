from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from app.core.database import get_db
from app.core.security import get_current_admin, get_current_user
from app.models.department import Department, user_departments
from app.models.user import User
from app.schemas.department import DepartmentCreate, DepartmentUpdate, DepartmentResponse

router = APIRouter()

def build_dept_tree(departments: list, parent_id=None):
    tree = []
    for dept in departments:
        if dept.parent_id == parent_id:
            children = build_dept_tree(departments, dept.id)
            direct_count = len(dept.members)
            children_count = sum(c.get("total_count", 0) for c in children)
            total_count = direct_count + children_count
            node = {
                "id": dept.id,
                "name": dept.name,
                "code": dept.code,
                "dingtalk_id": dept.dingtalk_id,
                "parent_id": dept.parent_id,
                "is_active": dept.is_active,
                "direct_count": direct_count,
                "total_count": total_count,
                "member_count": total_count,
                "children": children
            }
            tree.append(node)
    return tree

@router.get("/tree")
def get_department_tree(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    departments = db.query(Department).filter(Department.is_active == True).all()
    return build_dept_tree(departments)

@router.get("/", response_model=List[DepartmentResponse])
def list_departments(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(Department).filter(Department.is_active == True).all()

@router.get("/{dept_id}", response_model=DepartmentResponse)
def get_department(dept_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    dept = db.query(Department).filter(Department.id == dept_id).first()
    if not dept:
        raise HTTPException(status_code=404, detail="Department not found")
    return dept

@router.get("/{dept_id}/members")
def get_department_members(dept_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    dept = db.query(Department).filter(Department.id == dept_id).first()
    if not dept:
        raise HTTPException(status_code=404, detail="Department not found")
    members = dept.members
    return [{
        "id": m.id,
        "username": m.username,
        "full_name": m.full_name,
        "role": m.role,
        "is_department_admin": m.is_department_admin,
        "is_active": m.is_active,
        "dingtalk_userid": m.dingtalk_userid,
        "email": m.email
    } for m in members]

@router.post("/", response_model=DepartmentResponse)
def create_department(dept: DepartmentCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_admin)):
    db_dept = Department(**dept.model_dump())
    db.add(db_dept)
    db.commit()
    db.refresh(db_dept)
    return db_dept

@router.put("/{dept_id}", response_model=DepartmentResponse)
def update_department(dept_id: int, dept_update: DepartmentUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_admin)):
    dept = db.query(Department).filter(Department.id == dept_id).first()
    if not dept:
        raise HTTPException(status_code=404, detail="Department not found")
    for key, value in dept_update.model_dump(exclude_unset=True).items():
        setattr(dept, key, value)
    db.commit()
    db.refresh(dept)
    return dept

@router.delete("/{dept_id}")
def delete_department(dept_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_admin)):
    dept = db.query(Department).filter(Department.id == dept_id).first()
    if not dept:
        raise HTTPException(status_code=404, detail="Department not found")
    dept.is_active = False
    db.commit()
    return {"message": "Department deactivated"}
