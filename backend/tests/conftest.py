import os
os.environ.setdefault("ENVIRONMENT", "testing")
os.environ.setdefault("DATABASE_ENGINE", "sqlite")
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.core.database import Base, get_db
from app.core.security import get_password_hash
from app.core.migrations import (
    run_step2_migrations, run_step3_migrations, 
    run_step4_migrations, run_step5_security_and_ai_migrations
)
from app.models import models as app_models
from app.models.models import User, UserRole, Patient, Doctor, Department, DoctorSchedule
from datetime import time

TEST_DB_URL = "sqlite:///./test_unified.db"
test_engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

@pytest.fixture(scope="session", autouse=True)
def setup_database():
    if os.path.exists("./test_unified.db"):
        os.remove("./test_unified.db")
    Base.metadata.create_all(bind=test_engine)
    run_step2_migrations(test_engine)
    run_step3_migrations(test_engine)
    run_step4_migrations(test_engine)
    run_step5_security_and_ai_migrations(test_engine)
    yield
    if os.path.exists("./test_unified.db"):
        os.remove("./test_unified.db")

@pytest.fixture(scope="function")
def db_session():
    connection = test_engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture
def client(db_session):
    def _get_test_db():
        yield db_session

    app.dependency_overrides[get_db] = _get_test_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.pop(get_db, None)

