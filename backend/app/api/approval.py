from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional, List
from pydantic import BaseModel
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.knowledge import ApprovalChain, ApprovalInstance, ApprovalStep, Document
from datetime import datetime
import json

router = APIRouter()


class ChainCreate(BaseModel):
    name: str
    steps: List[dict]


class ChainUpdate(BaseModel):
    name: Optional[str] = None
    steps: Optional[List[dict]] = None
    is_active: Optional[bool] = None


class ApproveAction(BaseModel):
    approved: bool
    comment: Optional[str] = None


@router.get("/chains")
def list_chains(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="需要管理员权限")
    chains = db.query(ApprovalChain).all()
    result = []
    for c in chains:
        steps = json.loads(c.steps_config) if c.steps_config else []
        result.append({
            "id": c.id,
            "name": c.name,
            "steps": steps,
            "is_active": c.is_active,
            "created_at": c.created_at.isoformat() if c.created_at else None,
        })
    return result


@router.post("/chains")
def create_chain(chain: ChainCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="需要管理员权限")
    new_chain = ApprovalChain(
        name=chain.name,
        steps_config=json.dumps(chain.steps, ensure_ascii=False),
        created_by=current_user.id,
    )
    db.add(new_chain)
    db.commit()
    db.refresh(new_chain)
    return {"id": new_chain.id, "name": new_chain.name, "message": "审批链创建成功"}


@router.put("/chains/{chain_id}")
def update_chain(chain_id: int, chain_update: ChainUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="需要管理员权限")
    chain = db.query(ApprovalChain).filter(ApprovalChain.id == chain_id).first()
    if not chain:
        raise HTTPException(status_code=404, detail="审批链不存在")
    if chain_update.name is not None:
        chain.name = chain_update.name
    if chain_update.steps is not None:
        chain.steps_config = json.dumps(chain_update.steps, ensure_ascii=False)
    if chain_update.is_active is not None:
        chain.is_active = chain_update.is_active
    db.commit()
    return {"message": "审批链更新成功"}


@router.delete("/chains/{chain_id}")
def delete_chain(chain_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="需要管理员权限")
    chain = db.query(ApprovalChain).filter(ApprovalChain.id == chain_id).first()
    if not chain:
        raise HTTPException(status_code=404, detail="审批链不存在")
    chain.is_active = False
    db.commit()
    return {"message": "审批链已停用"}


@router.get("/pending")
def list_pending_approvals(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    instances = db.query(ApprovalInstance).filter(ApprovalInstance.status == "pending").all()
    result = []
    for inst in instances:
        current_step_record = db.query(ApprovalStep).filter(
            ApprovalStep.instance_id == inst.id,
            ApprovalStep.step_order == inst.current_step,
        ).first()
        if not current_step_record:
            continue
        can_approve = False
        if current_step_record.approver_type == "specific_user" and current_step_record.approver_id == current_user.id:
            can_approve = True
        elif current_step_record.approver_type == "department_admin":
            doc = db.query(Document).filter(Document.id == inst.document_id).first()
            if doc and doc.uploader:
                uploader_depts = doc.uploader.departments
                for dept in uploader_depts:
                    if dept.manager_id == current_user.id:
                        can_approve = True
                    dept_members = dept.members
                    for m in dept_members:
                        if m.id == current_user.id and m.is_department_admin:
                            can_approve = True
        elif current_step_record.approver_type == "kb_admin" and current_user.role == "admin":
            can_approve = True
        elif current_step_record.approver_type == "admin" and current_user.role == "admin":
            can_approve = True
        if can_approve:
            doc = db.query(Document).filter(Document.id == inst.document_id).first()
            all_steps = db.query(ApprovalStep).filter(ApprovalStep.instance_id == inst.id).order_by(ApprovalStep.step_order).all()
            result.append({
                "instance_id": inst.id,
                "document_id": inst.document_id,
                "doc_title": doc.title if doc else "未知",
                "kb_id": doc.kb_id if doc else None,
                "current_step": inst.current_step,
                "total_steps": len(all_steps),
                "steps": [{
                    "step_order": s.step_order,
                    "approver_type": s.approver_type,
                    "status": s.status,
                    "comment": s.comment,
                    "approver_name": s.approver.full_name if s.approver else None,
                } for s in all_steps],
                "created_at": inst.created_at.isoformat() if inst.created_at else None,
            })
    return result


@router.post("/instances/{instance_id}/action")
def approve_or_reject(instance_id: int, action: ApproveAction, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    inst = db.query(ApprovalInstance).filter(ApprovalInstance.id == instance_id).first()
    if not inst:
        raise HTTPException(status_code=404, detail="审批实例不存在")
    if inst.status != "pending":
        raise HTTPException(status_code=400, detail="该审批已处理")

    current_step_record = db.query(ApprovalStep).filter(
        ApprovalStep.instance_id == inst.id,
        ApprovalStep.step_order == inst.current_step,
    ).first()
    if not current_step_record:
        raise HTTPException(status_code=400, detail="当前步骤不存在")

    if action.approved:
        current_step_record.status = "approved"
        current_step_record.approver_id = current_user.id
        current_step_record.comment = action.comment
        current_step_record.approved_at = datetime.utcnow()

        next_step = db.query(ApprovalStep).filter(
            ApprovalStep.instance_id == inst.id,
            ApprovalStep.step_order == inst.current_step + 1,
        ).first()
        if next_step:
            inst.current_step += 1
        else:
            inst.status = "approved"
            doc = db.query(Document).filter(Document.id == inst.document_id).first()
            if doc:
                doc.status = "approved"
    else:
        current_step_record.status = "rejected"
        current_step_record.approver_id = current_user.id
        current_step_record.comment = action.comment
        current_step_record.approved_at = datetime.utcnow()
        inst.status = "rejected"
        doc = db.query(Document).filter(Document.id == inst.document_id).first()
        if doc:
            doc.status = "rejected"

    db.commit()
    return {"message": "审批通过" if action.approved else "审批驳回", "instance_status": inst.status}


@router.get("/instances")
def list_my_approval_history(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    steps = db.query(ApprovalStep).filter(ApprovalStep.approver_id == current_user.id).all()
    result = []
    for s in steps:
        inst = db.query(ApprovalInstance).filter(ApprovalInstance.id == s.instance_id).first()
        doc = db.query(Document).filter(Document.id == inst.document_id).first() if inst else None
        result.append({
            "instance_id": s.instance_id,
            "step_order": s.step_order,
            "status": s.status,
            "comment": s.comment,
            "doc_title": doc.title if doc else "未知",
            "approved_at": s.approved_at.isoformat() if s.approved_at else None,
        })
    return result
