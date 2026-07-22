"""Marketing navigation and quick actions."""

from __future__ import annotations

from investhome_api.models.user_auth import User
from investhome_api.schemas.marketing import (
    MarketingNavGroup,
    MarketingNavItem,
    MarketingNavigationResponse,
    MarketingQuickAction,
    MarketingQuickActionsResponse,
)
from investhome_api.services.permission_service import user_has_permission

NAV_GROUPS: list[MarketingNavGroup] = [
    MarketingNavGroup(
        key="overview",
        label_key="marketing.nav.groups.overview",
        items=[
            MarketingNavItem(href="/workspaces/marketing/dashboard", label_key="marketing.nav.dashboard", permission="view_dashboard"),
            MarketingNavItem(href="/workspaces/marketing/calendar", label_key="marketing.nav.calendar", permission="view"),
            MarketingNavItem(href="/workspaces/marketing/reports", label_key="marketing.nav.reports", permission="export_analytics"),
        ],
    ),
    MarketingNavGroup(
        key="demand_generation",
        label_key="marketing.nav.groups.demandGeneration",
        items=[
            MarketingNavItem(href="/workspaces/marketing/campaigns", label_key="marketing.nav.campaigns", permission="manage_campaigns"),
            MarketingNavItem(href="/workspaces/marketing/audiences", label_key="marketing.nav.audiences", permission="manage_audiences"),
            MarketingNavItem(href="/workspaces/marketing/segments", label_key="marketing.nav.segments", permission="manage_segments"),
            MarketingNavItem(href="/workspaces/marketing/leads", label_key="marketing.nav.leads", permission="view_leads"),
            MarketingNavItem(href="/workspaces/marketing/sources", label_key="marketing.nav.sources", permission="manage_campaigns"),
            MarketingNavItem(href="/workspaces/marketing/landing-pages", label_key="marketing.nav.landingPages", permission="manage_campaigns"),
            MarketingNavItem(href="/workspaces/marketing/forms", label_key="marketing.nav.forms", permission="manage_campaigns"),
        ],
    ),
    MarketingNavGroup(
        key="content",
        label_key="marketing.nav.groups.content",
        items=[
            MarketingNavItem(href="/workspaces/marketing/content", label_key="marketing.nav.contentStudio", permission="publish_content"),
            MarketingNavItem(href="/workspaces/marketing/social", label_key="marketing.nav.social", permission="publish_content"),
            MarketingNavItem(href="/workspaces/marketing/email", label_key="marketing.nav.email", permission="send_email"),
            MarketingNavItem(href="/workspaces/marketing/whatsapp", label_key="marketing.nav.whatsapp", permission="send_whatsapp"),
            MarketingNavItem(href="/workspaces/marketing/sms", label_key="marketing.nav.sms", permission="send_sms"),
            MarketingNavItem(href="/workspaces/marketing/templates", label_key="marketing.nav.templates", permission="publish_content"),
        ],
    ),
    MarketingNavGroup(
        key="paid_media",
        label_key="marketing.nav.groups.paidMedia",
        items=[
            MarketingNavItem(href="/workspaces/marketing/advertising", label_key="marketing.nav.advertising", permission="manage_advertising"),
            MarketingNavItem(href="/workspaces/marketing/budgets", label_key="marketing.nav.budgets", permission="manage_budgets"),
            MarketingNavItem(href="/workspaces/marketing/attribution", label_key="marketing.nav.attribution", permission="view_attribution"),
            MarketingNavItem(href="/workspaces/marketing/analytics", label_key="marketing.nav.analytics", permission="export_analytics"),
        ],
    ),
    MarketingNavGroup(
        key="operations",
        label_key="marketing.nav.groups.operations",
        items=[
            MarketingNavItem(href="/workspaces/marketing/events", label_key="marketing.nav.events", permission="manage_events"),
            MarketingNavItem(href="/workspaces/marketing/assets", label_key="marketing.nav.assets", permission="manage_assets"),
            MarketingNavItem(href="/workspaces/marketing/brand", label_key="marketing.nav.brand", permission="manage_brand"),
            MarketingNavItem(href="/workspaces/marketing/automations", label_key="marketing.nav.automations", permission="manage_automations"),
            MarketingNavItem(href="/workspaces/marketing/approvals", label_key="marketing.nav.approvals", permission="approve_content"),
            MarketingNavItem(href="/workspaces/marketing/vendors", label_key="marketing.nav.vendors", permission="manage_settings"),
        ],
    ),
    MarketingNavGroup(
        key="administration",
        label_key="marketing.nav.groups.administration",
        items=[
            MarketingNavItem(href="/workspaces/marketing/settings", label_key="marketing.nav.settings", permission="manage_settings"),
        ],
    ),
]

QUICK_ACTIONS: list[MarketingQuickAction] = [
    MarketingQuickAction(key="create_campaign", label_key="marketing.quickActions.createCampaign", href="/workspaces/marketing/campaigns", permission="manage_campaigns"),
    MarketingQuickAction(key="create_audience", label_key="marketing.quickActions.createAudience", href="/workspaces/marketing/audiences", permission="manage_audiences"),
    MarketingQuickAction(key="create_segment", label_key="marketing.quickActions.createSegment", href="/workspaces/marketing/segments", permission="manage_segments"),
    MarketingQuickAction(key="create_lead_source", label_key="marketing.quickActions.createLeadSource", href="/workspaces/marketing/sources", permission="manage_campaigns"),
    MarketingQuickAction(key="create_landing_page", label_key="marketing.quickActions.createLandingPage", href="/workspaces/marketing/landing-pages", permission="manage_campaigns"),
    MarketingQuickAction(key="create_form", label_key="marketing.quickActions.createForm", href="/workspaces/marketing/forms", permission="manage_campaigns"),
    MarketingQuickAction(key="create_content", label_key="marketing.quickActions.createContent", href="/workspaces/marketing/content", permission="publish_content"),
    MarketingQuickAction(key="schedule_social", label_key="marketing.quickActions.scheduleSocial", href="/workspaces/marketing/social", permission="publish_content"),
    MarketingQuickAction(key="email_campaign", label_key="marketing.quickActions.emailCampaign", href="/workspaces/marketing/email", permission="send_email"),
    MarketingQuickAction(key="whatsapp_campaign", label_key="marketing.quickActions.whatsappCampaign", href="/workspaces/marketing/whatsapp", permission="send_whatsapp"),
    MarketingQuickAction(key="create_event", label_key="marketing.quickActions.createEvent", href="/workspaces/marketing/events", permission="manage_events"),
    MarketingQuickAction(key="upload_asset", label_key="marketing.quickActions.uploadAsset", href="/workspaces/marketing/assets", permission="manage_assets"),
    MarketingQuickAction(key="request_approval", label_key="marketing.quickActions.requestApproval", href="/workspaces/marketing/approvals", permission="approve_content"),
    MarketingQuickAction(key="add_budget", label_key="marketing.quickActions.addBudget", href="/workspaces/marketing/budgets", permission="manage_budgets"),
    MarketingQuickAction(key="open_calendar", label_key="marketing.quickActions.openCalendar", href="/workspaces/marketing/calendar", permission="view"),
    MarketingQuickAction(key="open_analytics", label_key="marketing.quickActions.openAnalytics", href="/workspaces/marketing/analytics", permission="export_analytics"),
]


def _has_marketing_permission(user: User, action: str) -> bool:
    return user_has_permission(user, "marketing", action) or user_has_permission(user, "marketing", "view")


def build_navigation(user: User) -> MarketingNavigationResponse:
    filtered_groups: list[MarketingNavGroup] = []
    for group in NAV_GROUPS:
        items = [
            item
            for item in group.items
            if item.permission is None or _has_marketing_permission(user, item.permission)
        ]
        if items:
            filtered_groups.append(
                MarketingNavGroup(key=group.key, label_key=group.label_key, items=items)
            )
    return MarketingNavigationResponse(groups=filtered_groups)


def build_quick_actions(user: User) -> MarketingQuickActionsResponse:
    actions = [action for action in QUICK_ACTIONS if _has_marketing_permission(user, action.permission)]
    return MarketingQuickActionsResponse(actions=actions)
