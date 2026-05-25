import os, sys
os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.getcwd())
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
import uvicorn
print(f"Starting backend in {os.getcwd()}", flush=True)
uvicorn.run("app.main:app", host="127.0.0.1", port=8088, log_level="info")
