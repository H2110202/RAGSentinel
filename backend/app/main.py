from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import users, departments, auth, ragflow_proxy, dingtalk
from app.api import knowledge, approval, project_groups
from app.core.database import engine, Base
import app.models

Base.metadata.create_all(bind=engine)

app = FastAPI(title="RAGSentinel API", version="1.0.0", description="Enterprise-Grade Permission Gateway for RAG Knowledge Bases")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.include_router(auth.router, prefix="/api/auth", tags=["认证"])
app.include_router(users.router, prefix="/api/users", tags=["用户"])
app.include_router(departments.router, prefix="/api/departments", tags=["部门"])
app.include_router(ragflow_proxy.router, prefix="/api/ragflow", tags=["RAGFlow"])
app.include_router(dingtalk.router, prefix="/api", tags=["钉钉"])
app.include_router(knowledge.router, prefix="/api/knowledge", tags=["知识库"])
app.include_router(approval.router, prefix="/api/approval", tags=["审批"])
app.include_router(project_groups.router, prefix="/api/project-groups", tags=["项目组"])

@app.get("/")
def root():
    return {"message": "RAGSentinel API Running", "version": "1.0.0"}

@app.get("/health")
def health():
    return {"status": "ok"}
