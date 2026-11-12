"""Auth must not hold a pooled connection while asking for a second one."""

from __future__ import annotations

import threading
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool

from investhome_api.api.deps.auth import get_current_user
from investhome_api.config.settings import get_settings
from investhome_api.db.session import get_db
from investhome_api.models.security_enterprise import AuthSession
from investhome_api.models.user_auth import User, UserStatus
from investhome_api.services.session_service import touch_session

DEMO_PASSWORD = "Demo123!"


def _login(auth_client: TestClient, email: str = "admin@example.com") -> None:
    response = auth_client.post("/auth/login", json={"email": email, "password": DEMO_PASSWORD})
    assert response.status_code == 200, response.text


def _decode(token: str) -> dict:
    settings = get_settings()
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])


def test_authenticated_request_uses_one_connection_and_releases_it(auth_client: TestClient) -> None:
    import investhome_api.db.session as session_module

    _login(auth_client)
    state = {"out": 0, "max": 0}

    def on_checkout(*_args) -> None:
        state["out"] += 1
        state["max"] = max(state["max"], state["out"])

    def on_checkin(*_args) -> None:
        state["out"] = max(0, state["out"] - 1)

    event.listen(session_module.engine.pool, "checkout", on_checkout)
    event.listen(session_module.engine.pool, "checkin", on_checkin)

    from fastapi import Depends
    from sqlalchemy.orm import Session

    if not any(getattr(route, "path", None) == "/__auth_tx_probe" for route in auth_client.app.routes):

        @auth_client.app.get("/__auth_tx_probe")
        def auth_tx_probe(
            db: Session = Depends(get_db),
            user: User = Depends(get_current_user),
        ) -> dict:
            before = db.in_transaction()
            roles = [role.code for role in user.roles]
            permissions = [permission.action for role in user.roles for permission in role.permissions]
            return {
                "before": before,
                "after": db.in_transaction(),
                "email": user.email,
                "roles": roles,
                "permissions": len(permissions),
            }

    try:
        response = auth_client.get("/__auth_tx_probe")
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["before"] is False
        assert body["after"] is False
        assert body["email"] == "admin@example.com"
        assert body["roles"]
        assert body["permissions"] > 0
        assert state["max"] == 1
    finally:
        event.remove(session_module.engine.pool, "checkout", on_checkout)
        event.remove(session_module.engine.pool, "checkin", on_checkin)


def test_touch_and_cookie_refresh_do_not_open_sessionlocal(
    auth_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    import investhome_api.db.session as session_module

    _login(auth_client)
    token = auth_client.cookies.get("ih_session")
    assert token
    payload = _decode(token)
    near_exp = datetime.now(UTC) + timedelta(minutes=1)
    payload["exp"] = near_exp
    settings = get_settings()
    short_token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    db = session_module.SessionLocal()
    try:
        row = db.scalar(select(AuthSession).where(AuthSession.token_jti == payload["jti"]))
        assert row is not None
        row.expires_at = near_exp
        db.commit()
    finally:
        db.close()
    auth_client.cookies.set("ih_session", short_token)

    def refuse_second_session(*_args, **_kwargs):
        raise AssertionError("auth opened a second SessionLocal")

    monkeypatch.setattr(session_module, "SessionLocal", refuse_second_session)
    response = auth_client.get("/auth/me")
    assert response.status_code == 200, response.text
    assert response.json()["email"] == "admin@example.com"
    assert response.json()["permissions"]
    set_cookie = " ".join(
        value.decode() if isinstance(value, bytes) else value
        for key, value in response.headers.multi_items()
        if key.lower() == "set-cookie"
    )
    assert "ih_session=" in set_cookie.lower()


def test_permission_checks_still_apply(auth_client: TestClient) -> None:
    _login(auth_client, "admin@example.com")
    allowed = auth_client.get("/auth/me")
    assert allowed.status_code == 200
    assert "*:*" in allowed.json()["permissions"]

    _login(auth_client, "readonly@example.com")
    denied = auth_client.post(
        "/leads",
        json={
            "full_name": "Blocked Lead",
            "email": f"lead.{uuid4().hex[:8]}@example.com",
            "status": "new",
        },
    )
    assert denied.status_code == 403


def test_revoked_session_rolls_back_before_close(auth_client: TestClient) -> None:
    import investhome_api.db.session as session_module

    _login(auth_client)
    token = auth_client.cookies.get("ih_session")
    assert token
    assert auth_client.post("/auth/logout").status_code == 200
    auth_client.cookies.set("ih_session", token)
    seen: dict[str, bool] = {}

    def override():
        db = session_module.SessionLocal()
        try:
            yield db
        finally:
            seen["open"] = db.in_transaction()
            db.close()

    auth_client.app.dependency_overrides[get_db] = override
    response = auth_client.get("/auth/me")
    assert response.status_code == 401
    assert seen["open"] is False


def test_auth_exception_does_not_leak_transaction(
    auth_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    import investhome_api.db.session as session_module

    _login(auth_client)
    seen: dict[str, bool] = {}

    def override():
        db = session_module.SessionLocal()
        try:
            yield db
        finally:
            seen["open"] = db.in_transaction()
            db.close()

    auth_client.app.dependency_overrides[get_db] = override

    def boom(*_args, **_kwargs):
        raise RuntimeError("touch failed")

    monkeypatch.setattr("investhome_api.services.session_service.touch_session", boom)
    with pytest.raises(RuntimeError, match="touch failed"):
        auth_client.get("/auth/me")
    assert seen["open"] is False


def _tiny_engine(path):
    engine = create_engine(
        f"sqlite:///{path}",
        poolclass=QueuePool,
        pool_size=1,
        max_overflow=0,
        pool_timeout=1,
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(engine, "connect")
    def _busy(dbapi_connection, _record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA busy_timeout=3000")
        cursor.close()

    User.__table__.create(engine)
    AuthSession.__table__.create(engine)
    return engine


def _seed_stale_session(factory) -> str:
    db = factory()
    try:
        user = User(
            id=uuid4(),
            full_name="Pool User",
            email=f"pool-{uuid4().hex}@example.com",
            status=UserStatus.ACTIVE,
            hashed_password="x",
        )
        db.add(user)
        db.flush()
        jti = uuid4().hex
        stale = datetime.now(UTC) - timedelta(minutes=5)
        db.add(
            AuthSession(
                id=uuid4(),
                user_id=user.id,
                token_jti=jti,
                created_at=stale,
                last_seen_at=stale,
                expires_at=datetime.now(UTC) + timedelta(hours=2),
            )
        )
        db.commit()
        return jti
    finally:
        db.close()


def test_concurrent_touch_does_not_exhaust_a_one_connection_pool(tmp_path) -> None:
    engine = _tiny_engine(tmp_path / "auth-one.db")
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    jti = _seed_stale_session(factory)
    errors: list[BaseException] = []
    wrote: list[bool] = []
    lock = threading.Lock()

    def worker() -> None:
        db = factory()
        try:
            row = db.scalar(select(AuthSession).where(AuthSession.token_jti == jti))
            assert row is not None
            changed = touch_session(db, row)
            db.commit()
            assert not db.in_transaction()
            with lock:
                wrote.append(changed)
        except BaseException as exc:  # noqa: BLE001 - the test records pool timeouts
            with lock:
                errors.append(exc)
        finally:
            db.close()

    threads = [threading.Thread(target=worker) for _ in range(4)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=8)
    assert not any(thread.is_alive() for thread in threads)
    assert errors == []
    assert wrote.count(True) == 1
    db = factory()
    try:
        row = db.scalar(select(AuthSession).where(AuthSession.token_jti == jti))
        assert row is not None
        seen = row.last_seen_at
        if seen.tzinfo is None:
            seen = seen.replace(tzinfo=UTC)
        assert datetime.now(UTC) - seen < timedelta(seconds=30)
    finally:
        db.close()
    engine.dispose()


def test_concurrent_observed_timestamps_do_not_all_write(tmp_path) -> None:
    engine = create_engine(
        f"sqlite:///{tmp_path / 'auth-herd.db'}",
        poolclass=QueuePool,
        pool_size=6,
        max_overflow=0,
        pool_timeout=3,
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(engine, "connect")
    def _busy(dbapi_connection, _record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA busy_timeout=3000")
        cursor.close()

    User.__table__.create(engine)
    AuthSession.__table__.create(engine)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    jti = _seed_stale_session(factory)
    barrier = threading.Barrier(6)
    wrote: list[bool] = []
    errors: list[BaseException] = []
    lock = threading.Lock()
    max_out = {"value": 0, "current": 0}

    def on_checkout(*_args) -> None:
        max_out["current"] += 1
        max_out["value"] = max(max_out["value"], max_out["current"])

    def on_checkin(*_args) -> None:
        max_out["current"] -= 1

    event.listen(engine.pool, "checkout", on_checkout)
    event.listen(engine.pool, "checkin", on_checkin)

    def worker() -> None:
        db = factory()
        try:
            row = db.scalar(select(AuthSession).where(AuthSession.token_jti == jti))
            assert row is not None
            barrier.wait(timeout=5)
            changed = touch_session(db, row)
            db.commit()
            with lock:
                wrote.append(bool(changed))
        except BaseException as exc:  # noqa: BLE001
            with lock:
                errors.append(exc)
        finally:
            db.close()

    threads = [threading.Thread(target=worker) for _ in range(6)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=10)
    assert not any(thread.is_alive() for thread in threads)
    assert errors == []
    assert wrote.count(True) == 1
    assert max_out["value"] <= 6
    engine.dispose()


def test_role_load_happens_before_auth_session_write(
    auth_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    import investhome_api.api.deps.auth as auth_deps
    import investhome_api.db.session as session_module
    import investhome_api.services.session_service as session_service

    _login(auth_client)
    token = auth_client.cookies.get("ih_session")
    assert token
    payload = _decode(token)
    db = session_module.SessionLocal()
    try:
        row = db.scalar(select(AuthSession).where(AuthSession.token_jti == payload["jti"]))
        assert row is not None
        row.last_seen_at = datetime.now(UTC) - timedelta(minutes=5)
        db.commit()
    finally:
        db.close()

    order: list[str] = []
    sql_while_locked: list[str] = []
    locked = {"value": False}
    real_load = auth_deps.load_user_with_roles
    real_touch = session_service.touch_session
    real_commit = session_service.commit_auth_transaction

    def load(db, user_id):
        order.append("load_user_with_roles")
        assert locked["value"] is False
        user = real_load(db, user_id)
        assert user.roles
        assert any(role.permissions for role in user.roles)
        assert locked["value"] is False
        return user

    def touch(db, session):
        order.append("touch_session")
        locked["value"] = True
        try:
            return real_touch(db, session)
        finally:
            order.append("touch_returned")

    def commit(db):
        order.append("commit_auth_transaction")
        try:
            return real_commit(db)
        finally:
            locked["value"] = False

    def before_execute(_conn, _cursor, statement, _parameters, _context, _executemany) -> None:
        if locked["value"]:
            sql_while_locked.append(statement)

    monkeypatch.setattr(auth_deps, "load_user_with_roles", load)
    monkeypatch.setattr(session_service, "touch_session", touch)
    monkeypatch.setattr(session_service, "commit_auth_transaction", commit)
    event.listen(session_module.engine, "before_cursor_execute", before_execute)
    try:
        response = auth_client.get("/auth/me")
    finally:
        event.remove(session_module.engine, "before_cursor_execute", before_execute)

    assert response.status_code == 200, response.text
    assert order == [
        "load_user_with_roles",
        "touch_session",
        "touch_returned",
        "commit_auth_transaction",
    ]
    locked_sql = "\n".join(sql_while_locked).lower()
    assert "update" in locked_sql and "auth_sessions" in locked_sql
    assert "role_permissions" not in locked_sql
    assert "user_roles" not in locked_sql


def test_concurrent_requests_do_not_hold_session_lock_during_role_load(tmp_path, monkeypatch) -> None:
    import investhome_api.api.deps.auth as auth_deps
    from starlette.requests import Request
    from starlette.responses import Response

    from investhome_api.models.user_auth import Permission, Role, RolePermission, UserRole
    from investhome_api.services.auth_service import create_access_token

    engine = create_engine(
        f"sqlite:///{tmp_path / 'auth-lock.db'}",
        poolclass=QueuePool,
        pool_size=2,
        max_overflow=0,
        pool_timeout=1,
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(engine, "connect")
    def _busy(dbapi_connection, _record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=1000")
        cursor.close()

    for table in (
        User.__table__,
        Role.__table__,
        Permission.__table__,
        UserRole.__table__,
        RolePermission.__table__,
        AuthSession.__table__,
    ):
        table.create(engine)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    db = factory()
    try:
        user = User(
            id=uuid4(),
            full_name="Locked User",
            email=f"lock-{uuid4().hex}@example.com",
            status=UserStatus.ACTIVE,
            hashed_password="x",
        )
        role = Role(id=uuid4(), name="Sales", code=f"sales-{uuid4().hex[:8]}", is_system_role=False)
        permission = Permission(id=uuid4(), resource="leads", action="view")
        db.add_all([user, role, permission])
        db.flush()
        db.add(UserRole(id=uuid4(), user_id=user.id, role_id=role.id))
        db.add(RolePermission(id=uuid4(), role_id=role.id, permission_id=permission.id))
        jti = uuid4().hex
        stale = datetime.now(UTC) - timedelta(minutes=5)
        db.add(
            AuthSession(
                id=uuid4(),
                user_id=user.id,
                token_jti=jti,
                created_at=datetime.now(UTC) - timedelta(minutes=10),
                last_seen_at=stale,
                expires_at=datetime.now(UTC) + timedelta(hours=2),
            )
        )
        db.commit()
        user_id = user.id
    finally:
        db.close()

    monkeypatch.setenv("API_AUTH_ENABLED", "true")
    get_settings.cache_clear()
    token, _expires, _issued = create_access_token(user_id, jti=jti)
    local = threading.local()
    violations: list[str] = []
    real_load = auth_deps.load_user_with_roles

    def load(db, loaded_user_id):
        if getattr(local, "auth_write", False):
            violations.append("role load while auth_sessions update is uncommitted")
        user = real_load(db, loaded_user_id)
        assert user is not None
        assert user.roles and user.roles[0].permissions
        if getattr(local, "auth_write", False):
            violations.append("role permissions loaded while auth_sessions update is uncommitted")
        return user

    def before_execute(_conn, _cursor, statement, _parameters, _context, _executemany) -> None:
        text = statement.lower()
        if "update" in text and "auth_sessions" in text:
            local.auth_write = True
        if getattr(local, "auth_write", False) and (
            "role_permissions" in text or "user_roles" in text
        ):
            violations.append(statement)

    def on_commit(_conn) -> None:
        local.auth_write = False

    monkeypatch.setattr(auth_deps, "load_user_with_roles", load)
    event.listen(engine, "before_cursor_execute", before_execute)
    event.listen(engine, "commit", on_commit)
    errors: list[BaseException] = []
    emails: list[str] = []
    gate = threading.Lock()

    def worker() -> None:
        session = factory()
        try:
            scope = {
                "type": "http",
                "asgi": {"version": "3.0"},
                "http_version": "1.1",
                "method": "GET",
                "scheme": "http",
                "path": "/auth/me",
                "raw_path": b"/auth/me",
                "query_string": b"",
                "headers": [],
                "client": ("127.0.0.1", 123),
                "server": ("test", 80),
            }
            current = auth_deps.get_current_user(
                Request(scope),
                Response(),
                db=session,
                authorization=f"Bearer {token}",
                ih_session=None,
            )
            with gate:
                emails.append(current.email)
        except BaseException as exc:  # noqa: BLE001
            with gate:
                errors.append(exc)
        finally:
            session.close()

    threads = [threading.Thread(target=worker) for _ in range(4)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=8)
    event.remove(engine, "before_cursor_execute", before_execute)
    event.remove(engine, "commit", on_commit)
    engine.dispose()
    assert not any(thread.is_alive() for thread in threads)
    assert errors == []
    assert violations == []
    assert len(emails) == 4
