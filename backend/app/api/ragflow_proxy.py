from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from typing import Optional, List
from pydantic import BaseModel
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.knowledge import KnowledgeBase, Document
from app.core.config import config
from app.api.knowledge import check_kb_access, check_doc_access
import httpx
import os

router = APIRouter()

RAGFLOW_BASE = config.RAGFLOW_URL
RAGFLOW_HEADERS = {"Authorization": f"Bearer {config.RAGFLOW_API_KEY}"}


async def _ragflow_get(path: str, params: dict = None, timeout: float = 30):
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{RAGFLOW_BASE}{path}",
            headers=RAGFLOW_HEADERS,
            params=params,
            timeout=timeout,
        )
        return resp.json()


async def _ragflow_post(path: str, json_data: dict = None, timeout: float = 60):
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{RAGFLOW_BASE}{path}",
            headers={**RAGFLOW_HEADERS, "Content-Type": "application/json"},
            json=json_data,
            timeout=timeout,
        )
        return resp.json()


async def _ragflow_delete(path: str, json_data: dict = None, timeout: float = 30):
    async with httpx.AsyncClient() as client:
        resp = await client.delete(
            f"{RAGFLOW_BASE}{path}",
            headers={**RAGFLOW_HEADERS, "Content-Type": "application/json"},
            json=json_data,
            timeout=timeout,
        )
        return resp.json()


async def _ragflow_upload_file(path: str, dataset_id: str, file_path: str, file_name: str):
    async with httpx.AsyncClient(timeout=120) as client:
        with open(file_path, "rb") as f:
            files = {"file": (file_name, f)}
            resp = await client.post(
                f"{RAGFLOW_BASE}{path}",
                headers=RAGFLOW_HEADERS,
                data={"dataset_id": dataset_id},
                files=files,
            )
        return resp.json()


async def ragflow_create_dataset(name: str, description: str = "") -> dict:
    data = {
        "name": name,
        "chunk_method": config.RAGFLOW_CHUNK_METHOD,
        "permission": "me",
    }
    if description:
        data["description"] = description
    result = await _ragflow_post("/api/v1/datasets", data)
    if result.get("code") == 0:
        return {"success": True, "dataset_id": result["data"]["id"], "data": result["data"]}
    return {"success": False, "error": result.get("message", "未知错误"), "raw": result}


async def ragflow_delete_dataset(dataset_id: str) -> dict:
    result = await _ragflow_delete("/api/v1/datasets", {"ids": [dataset_id]})
    if result.get("code") == 0:
        return {"success": True}
    return {"success": False, "error": result.get("message", "未知错误"), "raw": result}


async def ragflow_upload_document(dataset_id: str, file_path: str, file_name: str) -> dict:
    result = await _ragflow_upload_file(
        "/api/v1/datasets/{dataset_id}/documents".replace("{dataset_id}", dataset_id),
        dataset_id,
        file_path,
        file_name,
    )
    if result.get("code") == 0:
        docs = result.get("data", [])
        doc_id = docs[0]["id"] if docs else None
        return {"success": True, "document_id": doc_id, "data": docs}
    return {"success": False, "error": result.get("message", "未知错误"), "raw": result}


async def ragflow_create_chat_assistant(name: str, dataset_ids: List[str], llm_model: str = None) -> dict:
    data = {
        "name": name,
        "dataset_ids": dataset_ids,
        "llm": {
            "model_name": llm_model or config.RAGFLOW_LLM_MODEL,
            "temperature": 0.1,
            "top_p": 0.9,
            "max_tokens": 2048,
        },
        "prompt": (
            "你是一个企业知识库智能助手。请严格基于检索到的知识库内容回答用户问题。"
            "如果知识库中没有相关信息，请明确告知用户，不要编造内容。"
            "回答要简洁、准确、有条理。"
        ),
    }
    result = await _ragflow_post("/api/v1/chats", data)
    if result.get("code") == 0:
        return {"success": True, "chat_id": result["data"]["id"], "data": result["data"]}
    return {"success": False, "error": result.get("message", "未知错误"), "raw": result}


async def ragflow_list_chats() -> dict:
    result = await _ragflow_get("/api/v1/chats", {"page": 1, "page_size": 100})
    if result.get("code") == 0:
        data = result.get("data", {})
        chats = data.get("chats", []) if isinstance(data, dict) else data
        return {"success": True, "data": chats}
    return {"success": False, "error": result.get("message", "未知错误")}


async def ragflow_chat_completion(chat_id: str, question: str, stream: bool = False) -> dict:
    data = {
        "model": config.RAGFLOW_LLM_MODEL.split("@")[0] if "@" in config.RAGFLOW_LLM_MODEL else config.RAGFLOW_LLM_MODEL,
        "messages": [{"role": "user", "content": question}],
        "stream": stream,
    }
    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(
            f"{RAGFLOW_BASE}/api/v1/openai/{chat_id}/chat/completions",
            headers={**RAGFLOW_HEADERS, "Content-Type": "application/json"},
            json=data,
        )
        if stream:
            return {"success": True, "stream": True, "raw": resp.text}
        result = resp.json()
        if "choices" in result:
            content = result["choices"][0]["message"]["content"] if result["choices"] else ""
            reference = result["choices"][0]["message"].get("reference", {})
            return {"success": True, "answer": content, "reference": reference, "raw": result}
        return {"success": False, "error": "RAGFlow返回格式异常", "raw": result}


async def ragflow_list_datasets() -> dict:
    result = await _ragflow_get("/api/v1/datasets", {"page": 1, "page_size": 100})
    if result.get("code") == 0:
        return {"success": True, "data": result.get("data", [])}
    return {"success": False, "error": result.get("message", "未知错误")}


@router.get("/status")
async def ragflow_status():
    try:
        result = await _ragflow_get("/api/v1/datasets", {"page": 1, "page_size": 1})
        if result.get("code") == 0:
            return {"connected": True, "url": RAGFLOW_BASE, "message": "RAGFlow连接正常"}
        return {"connected": False, "url": RAGFLOW_BASE, "message": result.get("message", "连接异常"), "raw": result}
    except Exception as e:
        return {"connected": False, "url": RAGFLOW_BASE, "message": f"无法连接RAGFlow: {str(e)}"}


@router.get("/datasets")
async def list_datasets(current_user: User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return await ragflow_list_datasets()


@router.post("/datasets")
async def create_dataset(name: str = "", current_user: User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="需要管理员权限")
    if not name:
        raise HTTPException(status_code=400, detail="请输入数据集名称")
    return await ragflow_create_dataset(name)


@router.get("/chats")
async def list_chats(current_user: User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return await ragflow_list_chats()


@router.post("/chats")
async def create_chat(name: str = "", dataset_ids: str = "", current_user: User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="需要管理员权限")
    if not name:
        raise HTTPException(status_code=400, detail="请输入助手名称")
    ids = [x.strip() for x in dataset_ids.split(",") if x.strip()] if dataset_ids else []
    return await ragflow_create_chat_assistant(name, ids)


class ChatRequest(BaseModel):
    chat_id: str
    question: str
    stream: bool = False


@router.post("/chat")
async def chat(req: ChatRequest, current_user: User = Depends(get_current_user)):
    if not req.chat_id or not req.question:
        raise HTTPException(status_code=400, detail="chat_id和question不能为空")
    return await ragflow_chat_completion(req.chat_id, req.question, req.stream)


class AgentChatRequest(BaseModel):
    dingtalk_userid: str
    question: str
    kb_ids: Optional[List[int]] = None


@router.post("/agent-chat")
async def agent_chat(req: AgentChatRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.dingtalk_userid == req.dingtalk_userid).first()
    if not user:
        raise HTTPException(status_code=403, detail="用户未找到")
    all_kbs = db.query(KnowledgeBase).filter(KnowledgeBase.is_active == True).all()
    accessible_dataset_ids = []
    accessible_kb_names = []
    for kb in all_kbs:
        if req.kb_ids and kb.id not in req.kb_ids:
            continue
        if not check_kb_access(user, kb, db, "view"):
            continue
        if kb.ragflow_dataset_id:
            accessible_dataset_ids.append(kb.ragflow_dataset_id)
            accessible_kb_names.append(kb.name)
    if not accessible_dataset_ids:
        return {"success": False, "answer": "您没有可访问的知识库，请联系管理员开通权限。", "accessible_kbs": []}
    chats_result = await ragflow_list_chats()
    chat_id = None
    if chats_result.get("success") and chats_result.get("data"):
        for c in chats_result["data"]:
            c_datasets = c.get("dataset_ids", [])
            if set(c_datasets) == set(accessible_dataset_ids):
                chat_id = c["id"]
                break
    if not chat_id:
        chat_name = f"perm_{user.id}_{','.join(accessible_kb_names[:3])}"
        create_result = await ragflow_create_chat_assistant(chat_name, accessible_dataset_ids)
        if not create_result.get("success"):
            return {"success": False, "answer": f"创建对话助手失败: {create_result.get('error', '未知错误')}"}
        chat_id = create_result["chat_id"]
    result = await ragflow_chat_completion(chat_id, req.question)
    if result.get("success"):
        return {
            "success": True,
            "answer": result["answer"],
            "reference": result.get("reference", {}),
            "accessible_kbs": accessible_kb_names,
            "chat_id": chat_id,
        }
    return {"success": False, "answer": f"查询失败: {result.get('error', '未知错误')}", "accessible_kbs": accessible_kb_names}
