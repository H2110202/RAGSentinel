import os, sys
os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.getcwd())
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
import uvicorn
host = os.getenv("HOST", "0.0.0.0")
port = int(os.getenv("PORT", "8088"))
print(f"Starting RAGSentinel API on {host}:{port}", flush=True)
uvicorn.run("app.main:app", host=host, port=port, log_level="info")
