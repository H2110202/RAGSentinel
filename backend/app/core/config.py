import os


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "CHANGE-ME-IN-PRODUCTION")
    ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))

    RAGFLOW_URL = os.getenv("RAGFLOW_URL", "http://localhost:9380")
    RAGFLOW_API_KEY = os.getenv("RAGFLOW_API_KEY", "")
    RAGFLOW_EMBEDDING_MODEL = os.getenv("RAGFLOW_EMBEDDING_MODEL", "BAAI/bge-large-zh-v1.5@BAAI")
    RAGFLOW_CHUNK_METHOD = os.getenv("RAGFLOW_CHUNK_METHOD", "naive")
    RAGFLOW_LLM_MODEL = os.getenv("RAGFLOW_LLM_MODEL", "deepseek-chat@DeepSeek")

    DINGTALK_APPID = os.getenv("DINGTALK_APPID", "")
    DINGTALK_APPSECRET = os.getenv("DINGTALK_APPSECRET", "")
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/permission_admin.db")

    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")


config = Config()
