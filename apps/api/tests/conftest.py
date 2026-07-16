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
from investhome_api.models.document import Document, DocumentAnalysis, DocumentLink  # noqa: F401
from investhome_api.models.document_intelligence import (  # noqa: F401
    AIUsage,
    DocumentChunk,
    DocumentConversation,
    DocumentMessage,
)
from investhome_api.models.drawing_intelligence import (  # noqa: F401
    DrawingAnalysis,
    DrawingAnnotation,
    DrawingElement,
    DrawingSheet,
    DrawingUnitProposal,
    DrawingVersionComparison,
)
from investhome_api.models.company_foundation import (  # noqa: F401
    BrandAsset,
    BrandProfile,
    CompanyProfile,
    Department,
    Office,
    SystemPreference,
    Team,
    UserDepartment,
    UserTeam,
)
from investhome_api.models.design_studio import (  # noqa: F401
    DesignProject,
    DesignVersion,
    FurnitureItem,
    MaterialPackage,
    StylePreset,
)
from investhome_api.models.inventory import (  # noqa: F401
    Building,
    Floor,
    InventoryAsset,
    InventoryAssetAssignment,
    InventoryAssetAssignmentEvent,
    InventoryAssetPrice,
    InventoryAssetStatusHistory,
    InventoryOwnership,
    InventoryOwnershipEvent,
    InventoryPriceEvent,
    InventoryReservation,
    InventoryReservationEvent,
    OwnershipApprovalRecord,
    OwnershipTransferParty,
    OwnershipTransferRequest,
    PriceApprovalRecord,
    PriceChangeRequest,
)
from investhome_api.models.sales import (  # noqa: F401
    OpportunityInventory,
    OpportunityProbabilityHistory,
    OpportunityProject,
    OpportunityTimeline,
    SalesOpportunity,
)
from investhome_api.models.sales_inventory_matching import (  # noqa: F401
    SalesInventoryMatch,
    SalesInventoryPreference,
    SalesInventoryPreferenceAssetType,
    SalesInventoryPreferenceBuilding,
    SalesInventoryPreferenceProject,
    SalesInventoryPreferenceUsageType,
    SalesShortlist,
    SalesShortlistItem,
)
from investhome_api.models.sales_proposal import (  # noqa: F401
    SalesProposal,
    SalesProposalActivity,
    SalesProposalApproval,
    SalesProposalItem,
    SalesProposalRecipient,
    SalesProposalVersion,
)
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
    monkeypatch.setenv("DOCUMENT_PROCESSING_SYNC", "true")
    get_settings.cache_clear()


@pytest.fixture
def client() -> TestClient:
    Base.metadata.create_all(bind=engine)

    import investhome_api.db.session as session_module

    original_engine = session_module.engine
    original_session_local = session_module.SessionLocal
    session_module.engine = engine
    session_module.SessionLocal = TestingSessionLocal

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    db = TestingSessionLocal()
    from investhome_api.models.design_studio import FurnitureItem, MaterialPackage, StylePreset

    if db.query(StylePreset).first() is None:
        for code, name in (
            ("modern", "Modern"),
            ("luxury", "Luxury"),
            ("scandinavian", "Scandinavian"),
            ("industrial", "Industrial"),
            ("minimalist", "Minimalist"),
        ):
            db.add(
                StylePreset(
                    name=name,
                    code=code,
                    description=f"{name} system preset",
                    color_palette={"primary": "#333333", "secondary": "#EEEEEE", "accent": "#999999"},
                    is_system_preset=True,
                )
            )
    if db.query(FurnitureItem).first() is None:
        for name, code, ftype, w, d, h in (
            ("Sofa", "sofa", "sofa", 220, 95, 85),
            ("Bed", "bed", "bed", 160, 210, 110),
            ("Dining Table", "dining_table", "dining_table", 180, 90, 75),
            ("Chair", "chair", "dining_chair", 45, 50, 85),
            ("Coffee Table", "coffee_table", "coffee_table", 120, 60, 45),
            ("Toilet", "toilet", "toilet", 40, 65, 80),
            ("Shower", "shower", "shower", 90, 90, 200),
            ("Kitchen Island", "kitchen_island", "kitchen_island", 180, 90, 90),
        ):
            db.add(
                FurnitureItem(
                    name=name,
                    code=code,
                    furniture_type=ftype,
                    width=w,
                    depth=d,
                    height=h,
                    is_system_item=True,
                )
            )
    if db.query(MaterialPackage).first() is None:
        for name, flooring in (
            ("Urban Loft Package", "Polished Concrete"),
            ("Coastal Calm Package", "Light Oak"),
            ("Warm Modern Package", "Wide Plank Oak"),
        ):
            db.add(MaterialPackage(name=name, flooring=flooring, wall_finish="Paint"))
    db.commit()
    db.close()
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    session_module.engine = original_engine
    session_module.SessionLocal = original_session_local
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db(client: TestClient):
    """SQLAlchemy session bound to the in-memory test database."""
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def auth_client(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("API_AUTH_ENABLED", "true")
    get_settings.cache_clear()

    from investhome_api.config.permissions_config import DEFAULT_ROLE_PERMISSIONS
    from investhome_api.models.user_auth import Permission, Role, RolePermission, User, UserRole, UserStatus
    from investhome_api.services.auth_service import hash_password

    db = TestingSessionLocal()
    permission_map: dict[tuple[str, str], Permission] = {}
    for resource in {
        "leads", "users", "roles", "executive", "activity", "finance", "investors", "projects",
        "notifications", "search", "documents", "inventory", "sales",
    }:
        for action in {
            "view", "create", "update", "manage", "archive", "restore", "manage_status", "download",
            "view_confidential", "view_highly_confidential",
            "analyze", "reprocess", "view_analysis", "ask", "export_analysis", "view_sensitive_analysis", "approve",
            "assign", "change_stage", "change_probability", "view_pipeline",
            "view_lead", "update_lead", "qualify_lead", "score_lead", "assign_lead",
            "view_documents", "upload_documents", "create_opportunity", "view_reservations",
            "export_lead", "view_inventory_matching", "save_inventory_preferences",
            "create_shortlist", "update_shortlist", "archive_shortlist", "add_inventory_match",
            "reject_inventory_match", "set_primary_inventory", "compare_inventory",
            "view_sensitive_inventory_price", "create_soft_hold", "request_reservation",
            "view_proposal", "create_proposal", "update_proposal", "submit_proposal",
            "review_proposal", "approve_proposal", "reject_proposal", "generate_proposal",
            "mark_proposal_sent", "mark_proposal_viewed", "mark_proposal_accepted",
            "view_sensitive_proposal_price", "archive_proposal",
            "view_price", "reserve", "release_hold", "request_reservation",
        }:
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
    for resource, action in (("documents", "view"), ("documents", "download"), ("inventory", "view")):
        db.add(
            RolePermission(
                role_id=roles["read_only"].id,
                permission_id=permission_map[(resource, action)].id,
            )
        )
    for resource in ("leads", "investors", "finance", "inventory"):
        for action in ("view", "create", "update", "archive", "restore", "manage_status"):
            key = (resource, action)
            if key not in permission_map:
                continue
            existing = (
                db.query(RolePermission)
                .filter_by(role_id=roles["super_admin"].id, permission_id=permission_map[key].id)
                .first()
            )
            if existing is None:
                db.add(
                    RolePermission(
                        role_id=roles["super_admin"].id,
                        permission_id=permission_map[key].id,
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
    for action in (
        "view", "create", "update", "archive", "download", "view_confidential", "view_highly_confidential",
        "analyze", "reprocess", "view_analysis", "ask", "export_analysis", "view_sensitive_analysis", "approve",
    ):
        db.add(
            RolePermission(
                role_id=roles["super_admin"].id,
                permission_id=permission_map[("documents", action)].id,
            )
        )
    for action in ("create", "update", "archive"):
        key = ("projects", action)
        if key not in permission_map:
            perm = Permission(resource="projects", action=action)
            db.add(perm)
            db.flush()
            permission_map[key] = perm
        existing = (
            db.query(RolePermission)
            .filter_by(role_id=roles["super_admin"].id, permission_id=permission_map[key].id)
            .first()
        )
        if existing is None:
            db.add(
                RolePermission(
                    role_id=roles["super_admin"].id,
                    permission_id=permission_map[key].id,
                )
            )
    for resource, action in (
        ("design", "view"),
        ("design", "create"),
        ("design", "update"),
        ("design", "save_version"),
        ("design", "approve"),
        ("design", "archive"),
        ("design", "manage_styles"),
        ("design", "manage_materials"),
        ("design", "manage_furniture"),
        ("design", "submit_review"),
    ):
        key = (resource, action)
        if key not in permission_map:
            perm = Permission(resource=resource, action=action)
            db.add(perm)
            db.flush()
            permission_map[key] = perm
        existing = (
            db.query(RolePermission)
            .filter_by(role_id=roles["super_admin"].id, permission_id=permission_map[key].id)
            .first()
        )
        if existing is None:
            db.add(
                RolePermission(
                    role_id=roles["super_admin"].id,
                    permission_id=permission_map[key].id,
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
