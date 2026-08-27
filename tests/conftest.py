"""
Fixtures partagées pour les tests SaveOS.

Base de données SQLite en mémoire (pas d'accès réseau ni de DB réelle,
conformément à AGENT.MD §5).
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from api.database import Base, get_db, Tenant, Agent, User
from api.main import app
from api.auth import AuthManager


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


@pytest.fixture()
def test_agent(db_session):
    """Crée un tenant + un agent de test et retourne (agent, token en clair)."""
    tenant = Tenant(
        name="test-tenant",
        registration_secret_hash=AuthManager.hash_token("test-registration-secret"),
    )
    db_session.add(tenant)
    db_session.commit()
    db_session.refresh(tenant)

    token = AuthManager.generate_agent_token()
    agent = Agent(
        tenant_id=tenant.id,
        hostname="test-host",
        platform="linux",
        token=AuthManager.hash_token(token),
        status="active",
    )
    db_session.add(agent)
    db_session.commit()
    db_session.refresh(agent)
    return agent, token


def _make_user(db_session, role, email, password="test-password"):
    """Crée un tenant + un utilisateur de test et retourne (user, mot de passe en clair)."""
    tenant = Tenant(
        name=f"tenant-for-{email}",
        registration_secret_hash=AuthManager.hash_token(f"secret-for-{email}"),
    )
    db_session.add(tenant)
    db_session.commit()
    db_session.refresh(tenant)

    user = User(
        tenant_id=tenant.id,
        email=email,
        role=role,
        password_hash=AuthManager.hash_password(password),
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user, password


@pytest.fixture()
def test_admin(db_session):
    """Crée un tenant + un utilisateur admin de test et retourne (user, mot de passe en clair)."""
    return _make_user(db_session, "admin", "admin@test.local")


@pytest.fixture()
def test_user(db_session):
    """Crée un tenant + un utilisateur (rôle user) de test et retourne (user, mot de passe en clair)."""
    return _make_user(db_session, "user", "user@test.local")
