"""G15A catalogs — architecture audit, modules, API scopes (no wildcards)."""

from __future__ import annotations

from investhome_api.models.platform_core import IntegrationStatus, ModuleLifecycleStatus

# Architecture reuse audit — honest statuses for G15A REPORT deliverable 1
ARCHITECTURE_AUDIT: list[dict] = [
    {
        "capability": "Auth / sessions / RBAC",
        "status": "LIVE",
        "reuse": "apps/api/.../deps/auth.py, permission_service, user_auth models",
        "notes": "Extend with platform resource; do not fork auth",
    },
    {
        "capability": "Feature flags (env)",
        "status": "LIVE",
        "reuse": "config/feature_flags.py FEATURE_*",
        "notes": "Extended with DB overrides + kill switch",
    },
    {
        "capability": "Feature flag overrides (DB)",
        "status": "LIVE",
        "reuse": "FeatureFlagOverride + /security/feature-flags",
        "notes": "G15A adds targeting columns + platform UI",
    },
    {
        "capability": "Platform API keys",
        "status": "PARTIAL",
        "reuse": "PlatformApiKey + Security Center CRUD",
        "notes": "Hashed secrets LIVE; request-auth middleware PARTIAL foundation",
    },
    {
        "capability": "Company Foundation branding",
        "status": "LIVE",
        "reuse": "BrandProfile + theme token injector",
        "notes": "No arbitrary CSS; G15A does not build white-label tenancy",
    },
    {
        "capability": "Activity / security audit",
        "status": "LIVE",
        "reuse": "activity + audit_service + admin audit",
        "notes": "Extended with platform external-access audit table",
    },
    {
        "capability": "In-app notifications",
        "status": "LIVE",
        "reuse": "notification_service",
        "notes": "Gateway abstraction PARTIAL (email/SMS NOT CONFIGURED)",
    },
    {
        "capability": "Notification gateway (email/SMS)",
        "status": "PARTIAL",
        "reuse": "services/notification_gateway.py + smtp_email.py",
        "notes": "Generic SMTP; not_connected until SMTP_HOST and SMTP_FROM_EMAIL are set",
    },
    {
        "capability": "Marketing webhooks",
        "status": "PARTIAL",
        "reuse": "marketing_webhooks routes",
        "notes": "Domain-specific; platform webhook bus is separate foundation",
    },
    {
        "capability": "Platform webhook bus",
        "status": "PARTIAL",
        "reuse": "platform_webhook_* + HMAC signing",
        "notes": "Signed enqueue + retry/dead-letter foundation; async dispatch later",
    },
    {
        "capability": "Integrations inventory",
        "status": "PARTIAL",
        "reuse": "Automation Center placeholders + platform_integrations",
        "notes": "Statuses honest — not Available unless working",
    },
    {
        "capability": "Module runtime registry",
        "status": "LIVE",
        "reuse": "platform_modules (G15A)",
        "notes": "Distinct from static modules/* manifests",
    },
    {
        "capability": "SaaS entitlements (access)",
        "status": "LIVE",
        "reuse": "platform_entitlements",
        "notes": "NOT billing — AND with flags/module/permission",
    },
    {
        "capability": "Billing / Stripe",
        "status": "BLOCKED",
        "reuse": "N/A",
        "notes": "Out of scope for G15A",
    },
    {
        "capability": "Contractor / Vendor / MGA / CMS / Mobile products",
        "status": "NOT REQUIRED",
        "reuse": "Registry rows only (Planned/Blocked)",
        "notes": "Do not implement product UIs in G15A",
    },
    {
        "capability": "Investor portal",
        "status": "PARTIAL",
        "reuse": "G9 /portal",
        "notes": "Existing — extend later, not rebuilt in G15A",
    },
    {
        "capability": "Analytics warehouse (G14)",
        "status": "PARTIAL",
        "reuse": "analytics schema",
        "notes": "Do not conflict; separate admin naming",
    },
    {
        "capability": "i18n TR/EN",
        "status": "LIVE",
        "reuse": "next-intl messages",
        "notes": "platformAdmin namespace",
    },
    {
        "capability": "Design system admin patterns",
        "status": "LIVE",
        "reuse": "admin shell, sec-ui, PageHeader",
        "notes": "Platform pages reuse sec-ui",
    },
]

# Full module registry list — products are Planned/Blocked rows only (no product UI in G15A)
MODULE_SEED: list[dict] = [
    {
        "code": "core_os",
        "name_en": "InvestHome OS Core",
        "name_tr": "InvestHome OS Çekirdek",
        "description_en": "Primary product foundation — always registered",
        "description_tr": "Birincil ürün temeli — her zaman kayıtlı",
        "lifecycle_status": ModuleLifecycleStatus.AVAILABLE.value,
        "enabled": True,
        "depends_on_json": [],
        "feature_flag_key": None,
        "route_prefix": "/dashboard",
        "admin_only": False,
        "pilot_phase": None,
        "sort_order": 1,
    },
    {
        "code": "platform_admin",
        "name_en": "Platform Admin",
        "name_tr": "Platform Yönetimi",
        "description_en": "G15A platform core administration",
        "description_tr": "G15A platform çekirdek yönetimi",
        "lifecycle_status": ModuleLifecycleStatus.AVAILABLE.value,
        "enabled": True,
        "depends_on_json": ["core_os"],
        "feature_flag_key": "platform_admin",
        "route_prefix": "/dashboard/admin/platform",
        "admin_only": True,
        "pilot_phase": "G15A",
        "sort_order": 2,
    },
    {
        "code": "security_center",
        "name_en": "Security Center",
        "name_tr": "Güvenlik Merkezi",
        "description_en": "Existing P11 security administration",
        "description_tr": "Mevcut P11 güvenlik yönetimi",
        "lifecycle_status": ModuleLifecycleStatus.AVAILABLE.value,
        "enabled": True,
        "depends_on_json": ["core_os"],
        "feature_flag_key": None,
        "route_prefix": "/dashboard/admin/security",
        "admin_only": True,
        "sort_order": 3,
    },
    {
        "code": "crm",
        "name_en": "CRM",
        "name_tr": "CRM",
        "description_en": "Existing CRM workspace",
        "description_tr": "Mevcut CRM çalışma alanı",
        "lifecycle_status": ModuleLifecycleStatus.AVAILABLE.value,
        "enabled": True,
        "depends_on_json": ["core_os"],
        "route_prefix": "/dashboard/crm",
        "sort_order": 10,
    },
    {
        "code": "projects",
        "name_en": "Projects",
        "name_tr": "Projeler",
        "description_en": "Existing projects domain",
        "description_tr": "Mevcut proje alanı",
        "lifecycle_status": ModuleLifecycleStatus.AVAILABLE.value,
        "enabled": True,
        "depends_on_json": ["core_os"],
        "route_prefix": "/dashboard",
        "sort_order": 11,
    },
    {
        "code": "finance",
        "name_en": "Finance",
        "name_tr": "Finans",
        "description_en": "Existing finance domain",
        "description_tr": "Mevcut finans alanı",
        "lifecycle_status": ModuleLifecycleStatus.AVAILABLE.value,
        "enabled": True,
        "depends_on_json": ["core_os"],
        "route_prefix": "/dashboard/finance",
        "sort_order": 12,
    },
    {
        "code": "investor_portal",
        "name_en": "Investor Portal",
        "name_tr": "Yatırımcı Portalı",
        "description_en": "Existing G9 portal — do not rebuild in G15A",
        "description_tr": "Mevcut G9 portal — G15A'da yeniden yazma",
        "lifecycle_status": ModuleLifecycleStatus.PARTIAL.value,
        "enabled": True,
        "depends_on_json": ["core_os"],
        "route_prefix": "/portal",
        "pilot_phase": "G9",
        "sort_order": 20,
    },
    {
        "code": "contractor_portal",
        "name_en": "Contractor Portal",
        "name_tr": "Yüklenici Portalı",
        "description_en": "Recommended G15B pilot — NOT implemented in G15A",
        "description_tr": "Önerilen G15B pilotu — G15A'da uygulanmadı",
        "lifecycle_status": ModuleLifecycleStatus.PLANNED.value,
        "enabled": False,
        "depends_on_json": ["core_os", "platform_admin", "projects"],
        "feature_flag_key": "contractor_portal",
        "route_prefix": None,
        "pilot_phase": "G15B",
        "sort_order": 30,
        "block_reason": "Awaiting G15A approval — do not build product UI yet",
    },
    {
        "code": "partner_workspace",
        "name_en": "Partner Workspace",
        "name_tr": "İş Ortağı Çalışma Alanı",
        "description_en": "Planned future phase",
        "description_tr": "Planlanan gelecek faz",
        "lifecycle_status": ModuleLifecycleStatus.PLANNED.value,
        "enabled": False,
        "depends_on_json": ["core_os", "platform_admin"],
        "feature_flag_key": "partner_workspace",
        "sort_order": 31,
        "block_reason": "No approved partner workflow",
    },
    {
        "code": "vendor_portal",
        "name_en": "Vendor Portal",
        "name_tr": "Tedarikçi Portalı",
        "description_en": "Planned — not in G15A sprint",
        "description_tr": "Planlandı — G15A sprintinde değil",
        "lifecycle_status": ModuleLifecycleStatus.PLANNED.value,
        "enabled": False,
        "depends_on_json": ["core_os", "platform_admin"],
        "feature_flag_key": "vendor_portal",
        "sort_order": 32,
        "block_reason": "No approved vendor workflow",
    },
    {
        "code": "agent_crm_lite",
        "name_en": "Agent CRM Lite",
        "name_tr": "Acenta CRM Lite",
        "description_en": "Planned — not in G15A sprint",
        "description_tr": "Planlandı — G15A sprintinde değil",
        "lifecycle_status": ModuleLifecycleStatus.PLANNED.value,
        "enabled": False,
        "depends_on_json": ["core_os", "crm"],
        "feature_flag_key": "agent_crm_lite",
        "sort_order": 33,
        "block_reason": "No approved agent workflow",
    },
    {
        "code": "asset_management",
        "name_en": "Asset Management",
        "name_tr": "Varlık Yönetimi",
        "description_en": "Planned — not in G15A sprint",
        "description_tr": "Planlandı — G15A sprintinde değil",
        "lifecycle_status": ModuleLifecycleStatus.PLANNED.value,
        "enabled": False,
        "depends_on_json": ["core_os", "projects"],
        "sort_order": 40,
        "block_reason": "Out of G15A scope",
    },
    {
        "code": "mobile_app",
        "name_en": "Mobile App",
        "name_tr": "Mobil Uygulama",
        "description_en": "Planned — not in G15A sprint",
        "description_tr": "Planlandı — G15A sprintinde değil",
        "lifecycle_status": ModuleLifecycleStatus.PLANNED.value,
        "enabled": False,
        "depends_on_json": ["core_os", "platform_admin"],
        "sort_order": 41,
        "block_reason": "Out of G15A scope",
    },
    {
        "code": "website_cms",
        "name_en": "Website CMS",
        "name_tr": "Web sitesi CMS",
        "description_en": "Planned — not in G15A sprint",
        "description_tr": "Planlandı — G15A sprintinde değil",
        "lifecycle_status": ModuleLifecycleStatus.PLANNED.value,
        "enabled": False,
        "depends_on_json": ["core_os"],
        "sort_order": 42,
        "block_reason": "Out of G15A scope",
    },
    {
        "code": "white_label",
        "name_en": "White-Label Tenancy",
        "name_tr": "Beyaz Etiket Kiracılık",
        "description_en": "Planned — tokens only later; no CSS injection ever",
        "description_tr": "Planlandı — sonra yalnızca belirteçler; CSS enjeksiyonu yok",
        "lifecycle_status": ModuleLifecycleStatus.PLANNED.value,
        "enabled": False,
        "depends_on_json": ["core_os", "platform_admin"],
        "sort_order": 50,
        "block_reason": "Out of G15A scope — await multi-tenant design",
    },
    {
        "code": "mga_insurance",
        "name_en": "MGA / Insurance",
        "name_tr": "MGA / Sigorta",
        "description_en": "BLOCKED — do not fabricate DIFC/DFSA/UAE rules",
        "description_tr": "ENGELLENDİ — DIFC/DFSA/BAE kuralları uydurulamaz",
        "lifecycle_status": ModuleLifecycleStatus.BLOCKED.value,
        "enabled": False,
        "depends_on_json": ["core_os", "platform_admin"],
        "feature_flag_key": "mga_insurance",
        "admin_only": True,
        "pilot_phase": "future",
        "sort_order": 90,
        "kill_switch": True,
        "block_reason": (
            "MGA BLOCKED for G15A/G15B. Regulatory rules require licensed counsel — "
            "never fabricate compliance logic."
        ),
    },
]

# Explicit scope catalog — NO wildcards (*, admin catch-alls forbidden for new clients)
API_SCOPE_CATALOG: list[dict] = [
    {
        "code": "platform:read",
        "name_en": "Platform read",
        "name_tr": "Platform okuma",
        "description_en": "Read platform registries and health",
        "category": "platform",
    },
    {
        "code": "platform:write",
        "name_en": "Platform write",
        "name_tr": "Platform yazma",
        "description_en": "Mutate platform configuration",
        "category": "platform",
    },
    {
        "code": "modules:read",
        "name_en": "Modules read",
        "name_tr": "Modül okuma",
        "description_en": "List module registry",
        "category": "modules",
    },
    {
        "code": "modules:write",
        "name_en": "Modules write",
        "name_tr": "Modül yazma",
        "description_en": "Enable/disable modules (non-blocked)",
        "category": "modules",
    },
    {
        "code": "flags:read",
        "name_en": "Flags read",
        "name_tr": "Bayrak okuma",
        "description_en": "Read feature flags",
        "category": "flags",
    },
    {
        "code": "flags:write",
        "name_en": "Flags write",
        "name_tr": "Bayrak yazma",
        "description_en": "Update feature flags and kill switches",
        "category": "flags",
    },
    {
        "code": "webhooks:manage",
        "name_en": "Webhooks manage",
        "name_tr": "Webhook yönet",
        "description_en": "Create subscriptions and enqueue deliveries",
        "category": "webhooks",
    },
    {
        "code": "integrations:read",
        "name_en": "Integrations read",
        "name_tr": "Entegrasyon okuma",
        "description_en": "List integration registry",
        "category": "integrations",
    },
    {
        "code": "audit:read",
        "name_en": "Audit read",
        "name_tr": "Denetim okuma",
        "description_en": "Read platform and external access audit",
        "category": "audit",
    },
    {
        "code": "entitlements:read",
        "name_en": "Entitlements read",
        "name_tr": "Yetki okuma",
        "description_en": "Read entitlements (not billing)",
        "category": "entitlements",
    },
    {
        "code": "external_users:read",
        "name_en": "External users read",
        "name_tr": "Dış kullanıcı okuma",
        "description_en": "Read external user type model",
        "category": "external_users",
    },
]

FORBIDDEN_SCOPES = frozenset({"*", "*:*", "admin", "admin:*", "all", "*.*"})

INTEGRATION_SEED: list[dict] = [
    {
        "code": "n8n",
        "name_en": "n8n Automation",
        "name_tr": "n8n Otomasyon",
        "category": "automation",
        "status": IntegrationStatus.PARTIAL.value,
        "description_en": "Sidecar present; FEATURE_N8N_AUTOMATION defaults false",
        "description_tr": "Sidecar mevcut; FEATURE_N8N_AUTOMATION varsayılan kapalı",
        "env_keys_json": ["FEATURE_N8N_AUTOMATION"],
        "sort_order": 1,
    },
    {
        "code": "smtp_email",
        "name_en": "SMTP Email",
        "name_tr": "SMTP E-posta",
        "category": "notifications",
        "status": IntegrationStatus.NOT_CONNECTED.value,
        "description_en": "Notification gateway — not connected",
        "description_tr": "Bildirim ağ geçidi — bağlı değil",
        "env_keys_json": ["SMTP_HOST", "SMTP_PORT", "SMTP_USERNAME", "SMTP_PASSWORD", "SMTP_USE_TLS", "SMTP_FROM_EMAIL", "SMTP_FROM_NAME", "APP_PUBLIC_URL"],
        "sort_order": 2,
    },
    {
        "code": "slack",
        "name_en": "Slack",
        "name_tr": "Slack",
        "category": "collaboration",
        "status": IntegrationStatus.PLANNED.value,
        "description_en": "Planned placeholder",
        "description_tr": "Planlandı yer tutucu",
        "env_keys_json": ["SLACK_BOT_TOKEN"],
        "sort_order": 3,
    },
    {
        "code": "stripe",
        "name_en": "Stripe Billing",
        "name_tr": "Stripe Faturalama",
        "category": "payments",
        "status": IntegrationStatus.BLOCKED.value,
        "description_en": "Billing out of scope — entitlements only",
        "description_tr": "Faturalama kapsam dışı — yalnızca yetkilendirmeler",
        "env_keys_json": [],
        "block_reason": "G15A entitlements access model only — no billing",
        "sort_order": 4,
    },
    {
        "code": "openai",
        "name_en": "External AI",
        "name_tr": "Harici AI",
        "category": "ai",
        "status": IntegrationStatus.NOT_CONNECTED.value,
        "description_en": "Human approval required for binding actions",
        "description_tr": "Bağlayıcı işlemler için insan onayı gerekir",
        "env_keys_json": ["FEATURE_EXTERNAL_AI", "AI_API_KEY"],
        "sort_order": 5,
    },
    {
        "code": "canva",
        "name_en": "Canva",
        "name_tr": "Canva",
        "category": "creative",
        "status": IntegrationStatus.NOT_CONNECTED.value,
        "description_en": "Connect Canva via OAuth 2.0 + PKCE",
        "description_tr": "Canva'yı OAuth 2.0 + PKCE ile bağlayın",
        "env_keys_json": ["CANVA_CLIENT_ID", "CANVA_CLIENT_SECRET"],
        "sort_order": 6,
    },
]


def detect_circular_dependencies(edges: list[tuple[str, str]]) -> list[str]:
    """Return list of nodes involved in a cycle, or empty if DAG."""
    graph: dict[str, list[str]] = {}
    for src, dst in edges:
        graph.setdefault(src, []).append(dst)
        graph.setdefault(dst, [])

    visiting: set[str] = set()
    visited: set[str] = set()
    cycle_nodes: list[str] = []

    def dfs(node: str, path: list[str]) -> bool:
        if node in visiting:
            # capture cycle slice
            if node in path:
                cycle_nodes.extend(path[path.index(node) :] + [node])
            return True
        if node in visited:
            return False
        visiting.add(node)
        path.append(node)
        for nxt in graph.get(node, []):
            if dfs(nxt, path):
                return True
        path.pop()
        visiting.remove(node)
        visited.add(node)
        return False

    for n in list(graph.keys()):
        if n not in visited and dfs(n, []):
            break
    return cycle_nodes


def validate_dependency_update(
    module_code: str,
    new_depends: list[str],
    all_deps: dict[str, list[str]],
) -> None:
    """Raise ValueError if update would create a cycle or unknown dep."""
    for dep in new_depends:
        if dep not in all_deps and dep != module_code:
            # allow unknown only if listed in catalog keys
            pass
    proposed = {**all_deps, module_code: list(new_depends)}
    edges: list[tuple[str, str]] = []
    for src, deps in proposed.items():
        for d in deps:
            edges.append((src, d))
    cycle = detect_circular_dependencies(edges)
    if cycle:
        raise ValueError(f"Circular dependency rejected: {' → '.join(cycle)}")


def deterministic_rollout(flag_key: str, subject_id: str, percent: int) -> bool:
    """Deterministic % rollout — same subject always gets same bucket."""
    if percent >= 100:
        return True
    if percent <= 0:
        return False
    digest = __import__("hashlib").sha256(f"{flag_key}:{subject_id}".encode()).hexdigest()
    bucket = int(digest[:8], 16) % 100
    return bucket < percent
