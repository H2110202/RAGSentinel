import os


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "change-this-secret-key-in-production")
    ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24

    RAGFLOW_URL = os.getenv("RAGFLOW_URL", "http://192.168.0.145:9380")
    RAGFLOW_API_KEY = os.getenv("RAGFLOW_API_KEY", "ragflow-3eac0efc580a11f189e19752856b1da9")
    RAGFLOW_EMBEDDING_MODEL = os.getenv("RAGFLOW_EMBEDDING_MODEL", "BAAI/bge-large-zh-v1.5@BAAI")
    RAGFLOW_CHUNK_METHOD = os.getenv("RAGFLOW_CHUNK_METHOD", "naive")
    RAGFLOW_LLM_MODEL = os.getenv("RAGFLOW_LLM_MODEL", "deepseek-chat@DeepSeek")

    DINGTALK_APPID = os.getenv("DINGTALK_APPID", "")
    DINGTALK_APPSECRET = os.getenv("DINGTALK_APPSECRET", "")
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./permission_admin.db")


config = Config()
