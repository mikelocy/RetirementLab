from sqlmodel import SQLModel, create_engine, Session
import os

# Import all models so SQLModel can create tables
from . import models  # noqa: F401

# Get the project root directory (one level up from backend/)
backend_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(backend_dir)
# Database file is in the project root
sqlite_file_name = os.path.join(project_root, "retirement_lab_v3.db")
sqlite_url = f"sqlite:///{sqlite_file_name}"

connect_args = {"check_same_thread": False}
engine = create_engine(sqlite_url, echo=True, connect_args=connect_args)

def init_db():
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session

