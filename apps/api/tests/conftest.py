"""Shared pytest fixtures with auth disabled for module tests."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from investhome_api.config.settings import get_settings
from investhome_api.db.base import Base
from investhome_api.db.session import get_db
from investhome_api.main import app
from investhome_api.models.activity import ActivityLog  # noqa: F401
from investhome_api.models.notification import Notification  # noqa: F401
from investhome_api.models.user_auth import Permission, Role, RolePermission, User, UserRole  # noqa: F401

SQLALCHEMY_DATABASE_URL = "sqlite+pysqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(autouse=True)
def _configure_auth(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch) -> None:
    enabled = "test_auth.py" in str(request.fspath)
    monkeypatch.setenv("API_AUTH_ENABLED", "true" if enabled else "false")
    get_settings.cache_clear()


@pytest.fixture
def client() -> TestClient:
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def auth_client(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("API_AUTH_ENABLED", "true")
    get_settings.cache_clear()

    from investhome_api.config.permissions_config import DEFAULT_ROLE_PERMISSIONS
    from investhome_api.models.user_auth import Permission, Role, RolePermission, User, UserRole, UserStatus
    from investhome_api.services.auth_service import hash_password

    db = TestingSessionLocal()
    permission_map: dict[tuple[str, str], Permission] = {}
    for resource in {"leads", "users", "roles", "executive", "activity", "finance", "investors", "projects", "notifications", "search"}:
        for action in {"view", "create", "update", "manage", "archive"}:
            key = (resource, action)
            if key in permission_map:
                continue
            perm = Permission(resource=resource, action=action)
            db.add(perm)
            permission_map[key] = perm
    db.flush()

    roles: dict[str, Role] = {}
    for code in ("super_admin", "sales", "read_only"):
        role = Role(name=code, code=code, is_system_role=True)
        db.add(role)
        roles[code] = role
    db.flush()

    for resource, action in DEFAULT_ROLE_PERMISSIONS["sales"]:
        if (resource, action) in permission_map:
            db.add(
                RolePermission(
                    role_id=roles["sales"].id,
                    permission_id=permission_map[(resource, action)].id,
                )
            )

    db.add(
        RolePermission(
            role_id=roles["read_only"].id,
            permission_id=permission_map[("leads", "view")].id,
        )
    )
    db.add(
        RolePermission(
            role_id=roles["read_only"].id,
            permission_id=permission_map[("activity", "view")].id,
        )
    )
    for resource in ("leads", "investors", "projects", "finance"):
        db.add(
            RolePermission(
                role_id=roles["super_admin"].id,
                permission_id=permission_map[(resource, "view")].id,
            )
        )
    db.add(
        RolePermission(
            role_id=roles["super_admin"].id,
            permission_id=permission_map[("activity", "view")].id,
        )
    )
    db.add(
        RolePermission(
            role_id=roles["super_admin"].id,
            permission_id=permission_map[("notifications", "view")].id,
        )
    )
    db.add(
        RolePermission(
            role_id=roles["super_admin"].id,
            permission_id=permission_map[("search", "view")].id,
        )
    )

    hashed = hash_password("Demo123!")
    specs = {
        "admin@example.com": "super_admin",
        "sales@example.com": "sales",
        "readonly@example.com": "read_only",
        "inactive@example.com": "read_only",
    }
    for email, role_code in specs.items():
        user = User(
            full_name=email.split("@")[0],
            email=email,
            hashed_password=hashed,
            status=UserStatus.INACTIVE if email.startswith("inactive") else UserStatus.ACTIVE,
        )
        db.add(user)
        db.flush()
        db.add(UserRole(user_id=user.id, role_id=roles[role_code].id))

    db.commit()
    db.close()
    return client
