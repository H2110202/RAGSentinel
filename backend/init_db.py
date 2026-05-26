import os
import sys

os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.getcwd())

from app.core.database import engine, SessionLocal, Base
from app.models.user import User
from app.core.security import get_password_hash
import app.models


def init_db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        admin = db.query(User).filter(User.username == "admin").first()
        if not admin:
            default_password = os.getenv("ADMIN_DEFAULT_PASSWORD", "changeme")
            admin = User(
                username="admin",
                email="admin@ragsentinel.local",
                full_name="System Administrator",
                hashed_password=get_password_hash(default_password),
                role="admin",
                is_active=True,
            )
            db.add(admin)
            db.commit()
            print(f"Default admin user created (username: admin, password: {default_password})")
            print("WARNING: Change the default password immediately after first login!")
        else:
            print("Admin user already exists, skipping.")
    finally:
        db.close()


if __name__ == "__main__":
    init_db()
