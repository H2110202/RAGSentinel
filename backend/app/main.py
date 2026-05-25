import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import users, departments, auth, ragflow_proxy, dingtalk
from app.api import knowledge, approval, project_groups
from app.core.database import engine, Base
from app.core.config import config
import app.models

logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("ragsentinel")

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="RAGSentinel API",
    version="1.0.0",
    description="Enterprise-Grade Permission Gateway for RAG Knowledge Bases",
    docs_url="/docs",
    redoc_url="/redoc",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.SECRET_KEY and ["*"] or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(users.router, prefix="/api/users", tags=["Users"])
app.include_router(departments.router, prefix="/api/departments", tags=["Departments"])
app.include_router(ragflow_proxy.router, prefix="/api/ragflow", tags=["RAGFlow"])
app.include_router(dingtalk.router, prefix="/api", tags=["DingTalk"])
app.include_router(knowledge.router, prefix="/api/knowledge", tags=["Knowledge Bases"])
app.include_router(approval.router, prefix="/api/approval", tags=["Approval"])
app.include_router(project_groups.router, prefix="/api/project-groups", tags=["Project Groups"])


@app.get("/")
def root():
    return {"message": "RAGSentinel API Running", "version": "1.0.0"}


@app.get("/health")
def health():
    checks = {"status": "ok", "version": "1.0.0", "checks": {}}
    try:
        from app.core.database import SessionLocal
        db = SessionLocal()
        db.execute(Base.metadata.tables["users"].select().limit(1))
        db.close()
        checks["checks"]["database"] = "ok"
    except Exception as e:
        checks["checks"]["database"] = f"error: {str(e)[:100]}"
        checks["status"] = "degraded"
    try:
        import httpx
        r = httpx.get(f"{config.RAGFLOW_URL}/api/v1/datasets", params={"page": 1, "page_size": 1}, headers={"Authorization": f"Bearer {config.RAGFLOW_API_KEY}"}, timeout=5)
        if r.status_code == 200:
            checks["checks"]["ragflow"] = "ok"
        else:
            checks["checks"]["ragflow"] = f"error: HTTP {r.status_code}"
            checks["status"] = "degraded"
    except Exception as e:
        checks["checks"]["ragflow"] = f"unreachable: {str(e)[:80]}"
        checks["status"] = "degraded"
    return checks
