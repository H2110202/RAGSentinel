from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import Optional, List
from pydantic import BaseModel
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.knowledge import KnowledgeBase, Document, KBPermission, DocumentPermission
from app.core.config import config
import httpx
import os
import uuid
import time

router = APIRouter()

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


class KBCreate(BaseModel):
    name: str
    description: Optional[str] = None
    is_public: bool = False


class KBUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_public: Optional[bool] = None


class PermissionCreate(BaseModel):
    target_type: str
    target_id: Optional[int] = None
    permission_level: str = "view"


class DocPermCreate(BaseModel):
    target_type: str
    target_id: Optional[int] = None
    permission_level: str = "view"


PERM_HIERARCHY = {
    "view": ["view", "download", "upload", "manage"],
    "download": ["download", "upload", "manage"],
    "upload": ["upload", "manage"],
    "manage": ["manage"],
}

_perm_cache: dict = {}
PERM_CACHE_TTL = 300


def _cache_key(user_id: int, resource_type: str, resource_id: int, required_level: str) -> str:
    return f"{user_id}:{resource_type}:{resource_id}:{required_level}"


def _get_cached(key: str):
    entry = _perm_cache.get(key)
    if entry and (time.time() - entry["ts"]) < PERM_CACHE_TTL:
        return entry["val"]
    if key in _perm_cache:
        del _perm_cache[key]
    return None


def _set_cached(key: str, val: bool):
    _perm_cache[key] = {"val": val, "ts": time.time()}


def invalidate_perm_cache(user_id: int = None):
    if user_id is None:
        _perm_cache.clear()
    else:
        prefix = f"{user_id}:"
        keys_to_del = [k for k in _perm_cache if k.startswith(prefix)]
        for k in keys_to_del:
            del _perm_cache[k]


def _match_target(p, user: User, db: Session) -> bool:
    if p.target_type == "company":
        return True
    elif p.target_type == "department":
        user_dept_ids = [d.id for d in user.departments]
        return p.target_id in user_dept_ids
    elif p.target_type == "individual":
        return p.target_id == user.id
    elif p.target_type == "project_group":
        from app.models.knowledge import ProjectGroupMember
        return db.query(ProjectGroupMember).filter(
            ProjectGroupMember.group_id == p.target_id,
            ProjectGroupMember.user_id == user.id
        ).first() is not None
    return False


def check_kb_access(user: User, kb: KnowledgeBase, db: Session, required_level="view") -> bool:
    if user.role == "admin":
        return True
    if kb.is_public and required_level == "view":
        return True
    if kb.created_by == user.id:
        return True

    ck = _cache_key(user.id, "kb", kb.id, required_level)
    cached = _get_cached(ck)
    if cached is not None:
        return cached

    perms = db.query(KBPermission).filter(KBPermission.kb_id == kb.id).all()
    allowed = PERM_HIERARCHY.get(required_level, [])
    result = False
    for p in perms:
        if p.permission_level not in allowed:
            continue
        if _match_target(p, user, db):
            result = True
            break

    _set_cached(ck, result)
    return result


def check_doc_access(user: User, doc: Document, db: Session, required_level="view") -> bool:
    if user.role == "admin":
        return True
    if doc.uploaded_by == user.id:
        return True

    kb = doc.knowledge_base
    if not check_kb_access(user, kb, db, required_level):
        return False

    doc_perms = db.query(DocumentPermission).filter(DocumentPermission.doc_id == doc.id).all()
    if not doc_perms:
        return True

    ck = _cache_key(user.id, "doc", doc.id, required_level)
    cached = _get_cached(ck)
    if cached is not None:
        return cached

    allowed = PERM_HIERARCHY.get(required_level, [])
    result = False
    for p in doc_perms:
        if p.permission_level not in allowed:
            continue
        if _match_target(p, user, db):
            result = True
            break

    _set_cached(ck, result)
    return result


def _perm_label(p, db: Session) -> str:
    if p.target_type == "company":
        return "全公司"
    elif p.target_type == "department":
        from app.models.department import Department
        dept = db.query(Department).filter(Department.id == p.target_id).first()
        return f"部门: {dept.name}" if dept else f"部门ID:{p.target_id}"
    elif p.target_type == "individual":
        u = db.query(User).filter(User.id == p.target_id).first()
        return f"个人: {u.full_name or u.username}" if u else f"用户ID:{p.target_id}"
    elif p.target_type == "project_group":
        from app.models.knowledge import ProjectGroup
        pg = db.query(ProjectGroup).filter(ProjectGroup.id == p.target_id).first()
        return f"项目组: {pg.name}" if pg else f"项目组ID:{p.target_id}"
    return str(p.target_id)


@router.get("/bases")
def list_knowledge_bases(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    all_kbs = db.query(KnowledgeBase).filter(KnowledgeBase.is_active == True).all()
    result = []
    for kb in all_kbs:
        if check_kb_access(current_user, kb, db, "view"):
            doc_count = db.query(Document).filter(Document.kb_id == kb.id).count()
            perms = db.query(KBPermission).filter(KBPermission.kb_id == kb.id).all()
            perm_summary = []
            for p in perms:
                label = _perm_label(p, db)
                perm_summary.append({"id": p.id, "type": p.target_type, "label": label, "level": p.permission_level})
            result.append({
                "id": kb.id,
                "name": kb.name,
                "description": kb.description,
                "is_public": kb.is_public,
                "created_by": kb.created_by,
                "creator_name": kb.creator.full_name if kb.creator else None,
                "doc_count": doc_count,
                "permissions": perm_summary,
                "created_at": kb.created_at.isoformat() if kb.created_at else None,
            })
    return result


@router.post("/bases")
async def create_knowledge_base(kb: KBCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    new_kb = KnowledgeBase(
        name=kb.name,
        description=kb.description,
        is_public=kb.is_public,
        created_by=current_user.id,
    )
    db.add(new_kb)
    db.commit()
    db.refresh(new_kb)
    perm = KBPermission(
        kb_id=new_kb.id,
        target_type="individual",
        target_id=current_user.id,
        permission_level="manage",
    )
    db.add(perm)
    db.commit()
    invalidate_perm_cache()
    ragflow_msg = ""
    try:
        from app.api.ragflow_proxy import ragflow_create_dataset
        rf_result = await ragflow_create_dataset(kb.name, kb.description or "")
        if rf_result.get("success"):
            new_kb.ragflow_dataset_id = rf_result["dataset_id"]
            db.commit()
            ragflow_msg = f"，RAGFlow Dataset已创建({rf_result['dataset_id'][:8]}...)"
        else:
            ragflow_msg = f"，RAGFlow同步失败: {rf_result.get('error', '未知')}"
    except Exception as e:
        ragflow_msg = f"，RAGFlow未连接: {str(e)[:50]}"
    return {"id": new_kb.id, "name": new_kb.name, "message": f"知识库创建成功{ragflow_msg}"}


@router.put("/bases/{kb_id}")
def update_knowledge_base(kb_id: int, kb_update: KBUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")
    if not check_kb_access(current_user, kb, db, "manage"):
        raise HTTPException(status_code=403, detail="无管理权限")
    for key, value in kb_update.model_dump(exclude_unset=True).items():
        setattr(kb, key, value)
    db.commit()
    invalidate_perm_cache()
    return {"message": "更新成功"}


@router.delete("/bases/{kb_id}")
def delete_knowledge_base(kb_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")
    if not check_kb_access(current_user, kb, db, "manage"):
        raise HTTPException(status_code=403, detail="无管理权限")
    kb.is_active = False
    db.commit()
    invalidate_perm_cache()
    return {"message": "知识库已删除"}


@router.get("/bases/{kb_id}/permissions")
def list_kb_permissions(kb_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")
    if not check_kb_access(current_user, kb, db, "view"):
        raise HTTPException(status_code=403, detail="无查看权限")
    perms = db.query(KBPermission).filter(KBPermission.kb_id == kb_id).all()
    return [{
        "id": p.id,
        "target_type": p.target_type,
        "target_id": p.target_id,
        "target_name": _perm_label(p, db),
        "permission_level": p.permission_level,
    } for p in perms]


@router.post("/bases/{kb_id}/permissions")
def set_permission(kb_id: int, perm: PermissionCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")
    if not check_kb_access(current_user, kb, db, "manage"):
        raise HTTPException(status_code=403, detail="无管理权限")
    existing = db.query(KBPermission).filter(
        KBPermission.kb_id == kb_id,
        KBPermission.target_type == perm.target_type,
        KBPermission.target_id == perm.target_id,
    ).first()
    if existing:
        existing.permission_level = perm.permission_level
    else:
        new_perm = KBPermission(
            kb_id=kb_id,
            target_type=perm.target_type,
            target_id=perm.target_id,
            permission_level=perm.permission_level,
        )
        db.add(new_perm)
    db.commit()
    invalidate_perm_cache()
    return {"message": "权限设置成功"}


@router.delete("/bases/{kb_id}/permissions/{perm_id}")
def remove_permission(kb_id: int, perm_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")
    if not check_kb_access(current_user, kb, db, "manage"):
        raise HTTPException(status_code=403, detail="无管理权限")
    perm = db.query(KBPermission).filter(KBPermission.id == perm_id).first()
    if perm:
        db.delete(perm)
        db.commit()
        invalidate_perm_cache()
    return {"message": "权限已移除"}


@router.get("/bases/{kb_id}/documents")
def list_documents(kb_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")
    if not check_kb_access(current_user, kb, db, "view"):
        raise HTTPException(status_code=403, detail="无查看权限")
    docs = db.query(Document).filter(Document.kb_id == kb_id).all()
    result = []
    for d in docs:
        has_doc_perm = db.query(DocumentPermission).filter(DocumentPermission.doc_id == d.id).count() > 0
        result.append({
            "id": d.id,
            "title": d.title,
            "file_type": d.file_type,
            "file_size": d.file_size,
            "status": d.status,
            "uploaded_by": d.uploaded_by,
            "uploader_name": d.uploader.full_name if d.uploader else None,
            "chunk_num": d.chunk_num,
            "has_doc_perm": has_doc_perm,
            "created_at": d.created_at.isoformat() if d.created_at else None,
        })
    return result


@router.post("/bases/{kb_id}/upload")
async def upload_document(kb_id: int, file: UploadFile = File(...), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")
    if not check_kb_access(current_user, kb, db, "upload"):
        raise HTTPException(status_code=403, detail="无上传权限")

    file_ext = os.path.splitext(file.filename)[1] if file.filename else ""
    file_id = str(uuid.uuid4())
    save_path = os.path.join(UPLOAD_DIR, f"{file_id}{file_ext}")
    content = await file.read()
    with open(save_path, "wb") as f:
        f.write(content)

    doc = Document(
        kb_id=kb_id,
        title=file.filename or "未命名文件",
        file_path=save_path,
        file_type=file_ext.lstrip("."),
        file_size=len(content),
        uploaded_by=current_user.id,
        status="pending",
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    from app.models.knowledge import ApprovalChain, ApprovalInstance, ApprovalStep
    chain = db.query(ApprovalChain).filter(ApprovalChain.is_active == True).first()
    if chain:
        import json
        steps_config = json.loads(chain.steps_config)
        instance = ApprovalInstance(
            document_id=doc.id,
            chain_id=chain.id,
            current_step=0,
            status="pending",
        )
        db.add(instance)
        db.flush()
        for i, step_cfg in enumerate(steps_config):
            approver_id = None
            if step_cfg.get("approver_type") == "specific_user":
                approver_id = step_cfg.get("approver_id")
            elif step_cfg.get("approver_type") == "department_admin":
                approver_id = None
            step = ApprovalStep(
                instance_id=instance.id,
                step_order=i,
                approver_type=step_cfg.get("approver_type", "department_admin"),
                approver_id=approver_id,
                status="pending",
            )
            db.add(step)
        db.commit()

    ragflow_msg = await _sync_doc_to_ragflow(kb, doc, db)
    return {"id": doc.id, "title": doc.title, "status": doc.status, "message": "文件上传成功，等待审批", "ragflow_sync": ragflow_msg}


async def _sync_doc_to_ragflow(kb: KnowledgeBase, doc: Document, db: Session) -> str:
    if not kb.ragflow_dataset_id or not doc.file_path or not os.path.exists(doc.file_path):
        return "跳过(RAGFlow未连接或文件不存在)"
    try:
        from app.api.ragflow_proxy import ragflow_upload_document
        rf_result = await ragflow_upload_document(
            kb.ragflow_dataset_id, doc.file_path, doc.title
        )
        if rf_result.get("success"):
            doc.ragflow_document_id = rf_result["document_id"]
            db.commit()
            return f"已同步({rf_result['document_id'][:8]}...)"
        return f"失败: {rf_result.get('error', '未知')}"
    except Exception as e:
        return f"异常: {str(e)[:50]}"


@router.post("/bases/{kb_id}/documents/{doc_id}/publish")
def publish_document(kb_id: int, doc_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    doc = db.query(Document).filter(Document.id == doc_id, Document.kb_id == kb_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")
    if doc.status != "approved":
        raise HTTPException(status_code=400, detail="文档未通过审批")
    doc.status = "published"
    db.commit()
    return {"message": "文档已发布"}


@router.get("/bases/{kb_id}/documents/{doc_id}/permissions")
def list_doc_permissions(kb_id: int, doc_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")
    if not check_kb_access(current_user, kb, db, "manage"):
        raise HTTPException(status_code=403, detail="无管理权限")
    doc = db.query(Document).filter(Document.id == doc_id, Document.kb_id == kb_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")
    perms = db.query(DocumentPermission).filter(DocumentPermission.doc_id == doc_id).all()
    return [{
        "id": p.id,
        "target_type": p.target_type,
        "target_id": p.target_id,
        "target_name": _perm_label(p, db),
        "permission_level": p.permission_level,
    } for p in perms]


@router.post("/bases/{kb_id}/documents/{doc_id}/permissions")
def set_doc_permission(kb_id: int, doc_id: int, perm: DocPermCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")
    if not check_kb_access(current_user, kb, db, "manage"):
        raise HTTPException(status_code=403, detail="无管理权限")
    doc = db.query(Document).filter(Document.id == doc_id, Document.kb_id == kb_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")
    existing = db.query(DocumentPermission).filter(
        DocumentPermission.doc_id == doc_id,
        DocumentPermission.target_type == perm.target_type,
        DocumentPermission.target_id == perm.target_id,
    ).first()
    if existing:
        existing.permission_level = perm.permission_level
    else:
        new_perm = DocumentPermission(
            doc_id=doc_id,
            target_type=perm.target_type,
            target_id=perm.target_id,
            permission_level=perm.permission_level,
        )
        db.add(new_perm)
    db.commit()
    invalidate_perm_cache()
    return {"message": "文档权限设置成功"}


@router.delete("/bases/{kb_id}/documents/{doc_id}/permissions/{perm_id}")
def remove_doc_permission(kb_id: int, doc_id: int, perm_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")
    if not check_kb_access(current_user, kb, db, "manage"):
        raise HTTPException(status_code=403, detail="无管理权限")
    perm = db.query(DocumentPermission).filter(DocumentPermission.id == perm_id, DocumentPermission.doc_id == doc_id).first()
    if perm:
        db.delete(perm)
        db.commit()
        invalidate_perm_cache()
    return {"message": "文档权限已移除"}


class AgentQueryRequest(BaseModel):
    dingtalk_userid: str
    kb_ids: Optional[List[int]] = None


@router.post("/agent/check-access")
def agent_check_access(req: AgentQueryRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.dingtalk_userid == req.dingtalk_userid).first()
    if not user:
        return {"has_access": False, "accessible_kbs": [], "reason": "用户未找到"}
    all_kbs = db.query(KnowledgeBase).filter(KnowledgeBase.is_active == True).all()
    accessible = []
    for kb in all_kbs:
        if check_kb_access(user, kb, db, "view"):
            if req.kb_ids and kb.id not in req.kb_ids:
                continue
            perm_level = "none"
            if check_kb_access(user, kb, db, "manage"):
                perm_level = "manage"
            elif check_kb_access(user, kb, db, "upload"):
                perm_level = "upload"
            elif check_kb_access(user, kb, db, "download"):
                perm_level = "download"
            elif check_kb_access(user, kb, db, "view"):
                perm_level = "view"
            accessible.append({
                "kb_id": kb.id,
                "kb_name": kb.name,
                "permission_level": perm_level,
                "is_public": kb.is_public,
            })
    return {
        "has_access": len(accessible) > 0,
        "user_id": user.id,
        "user_name": user.full_name or user.username,
        "accessible_kbs": accessible,
        "total_kbs": len(all_kbs),
        "accessible_count": len(accessible),
    }


class AgentQueryKB(BaseModel):
    kb_id: int
    dingtalk_userid: str


@router.post("/agent/query")
def agent_query_kb(req: AgentQueryKB, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.dingtalk_userid == req.dingtalk_userid).first()
    if not user:
        raise HTTPException(status_code=403, detail="用户未找到，无权访问")
    kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == req.kb_id, KnowledgeBase.is_active == True).first()
    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")
    if not check_kb_access(user, kb, db, "view"):
        raise HTTPException(status_code=403, detail="无权访问该知识库")
    docs = db.query(Document).filter(Document.kb_id == req.kb_id, Document.status == "published").all()
    accessible_docs = []
    for d in docs:
        if check_doc_access(user, d, db, "view"):
            accessible_docs.append({
                "id": d.id,
                "title": d.title,
                "file_type": d.file_type,
                "chunk_num": d.chunk_num,
                "ragflow_document_id": d.ragflow_document_id,
            })
    return {
        "kb_id": kb.id,
        "kb_name": kb.name,
        "documents": accessible_docs,
        "can_download": check_kb_access(user, kb, db, "download"),
    }


class AgentDocQuery(BaseModel):
    dingtalk_userid: str
    doc_ids: Optional[List[int]] = None


@router.post("/agent/filter-docs")
def agent_filter_docs(req: AgentDocQuery, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.dingtalk_userid == req.dingtalk_userid).first()
    if not user:
        return {"accessible_doc_ids": [], "reason": "用户未找到"}
    if req.doc_ids:
        docs = db.query(Document).filter(Document.id.in_(req.doc_ids), Document.status == "published").all()
    else:
        docs = db.query(Document).filter(Document.status == "published").all()
    accessible = []
    for d in docs:
        if check_doc_access(user, d, db, "view"):
            accessible.append(d.id)
    return {
        "user_id": user.id,
        "user_name": user.full_name or user.username,
        "requested_count": len(req.doc_ids) if req.doc_ids else len(docs),
        "accessible_doc_ids": accessible,
        "accessible_count": len(accessible),
    }
