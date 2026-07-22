"""Automation Center — aggregates marketing automations, ARQ cron, and integration status."""

from __future__ import annotations

import math
import os
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import String, cast, func, select
from sqlalchemy.orm import Session

from investhome_api.config.feature_flags import get_feature_flags
from investhome_api.config.settings import get_settings
from investhome_api.models.activity import ActivityEntityType, ActivityLog
from investhome_api.models.marketing_automation import (
    MarketingAutomationExecution,
    MarketingAutomationExecutionStatus,
    MarketingAutomationWorkflow,
    MarketingAutomationWorkflowStatus,
)
from investhome_api.services.marketing.automation_service import (
    execution_engine_message,
    is_execution_engine_available,
)

# ARQ cron catalog — mirrors WorkerSettings.cron_jobs (source of truth for schedules).
ARQ_SCHEDULED_JOBS: list[dict[str, Any]] = [
    {
        "id": "system:inventory_expire_soft_holds",
        "name": "Expire soft holds",
        "category": "projects",
        "cadence": "custom",
        "cadence_label": "Every 15 minutes",
        "cron_expression": "*/15 * * * *",
        "description": "Inventory soft-hold expiry worker.",
    },
    {
        "id": "system:inventory_reservation_reminders",
        "name": "Reservation reminders",
        "category": "notifications",
        "cadence": "custom",
        "cadence_label": "Twice hourly (:05, :35)",
        "cron_expression": "5,35 * * * *",
        "description": "Sends reservation reminder notifications.",
    },
    {
        "id": "system:inventory_overdue_deposits",
        "name": "Overdue deposits",
        "category": "finance",
        "cadence": "custom",
        "cadence_label": "Twice hourly (:10, :40)",
        "cron_expression": "10,40 * * * *",
        "description": "Flags overdue reservation deposits.",
    },
    {
        "id": "system:inventory_apply_scheduled_transfers",
        "name": "Apply scheduled ownership transfers",
        "category": "projects",
        "cadence": "custom",
        "cadence_label": "Twice hourly (:00, :30)",
        "cron_expression": "0,30 * * * *",
        "description": "Applies ownership transfers that reached their schedule.",
    },
    {
        "id": "system:inventory_apply_scheduled_assignments",
        "name": "Apply scheduled assignments",
        "category": "projects",
        "cadence": "custom",
        "cadence_label": "Twice hourly (:00, :30)",
        "cron_expression": "0,30 * * * *",
        "description": "Applies inventory assignments that reached their schedule.",
    },
    {
        "id": "system:work_due_soon",
        "name": "Work items due soon",
        "category": "crm",
        "cadence": "custom",
        "cadence_label": "Twice hourly (:20, :50)",
        "cron_expression": "20,50 * * * *",
        "description": "Notifies assignees of work items due soon.",
    },
    {
        "id": "system:work_overdue",
        "name": "Work items overdue",
        "category": "crm",
        "cadence": "custom",
        "cadence_label": "Twice hourly (:25, :55)",
        "cron_expression": "25,55 * * * *",
        "description": "Notifies assignees of overdue work items.",
    },
    {
        "id": "system:work_meeting_approaching",
        "name": "Meeting approaching",
        "category": "notifications",
        "cadence": "custom",
        "cadence_label": "Every 5 minutes",
        "cron_expression": "*/5 * * * *",
        "description": "Meeting approaching reminders.",
    },
    {
        "id": "system:work_follow_up_due",
        "name": "Follow-up due",
        "category": "crm",
        "cadence": "hourly",
        "cadence_label": "Hourly at :30",
        "cron_expression": "30 * * * *",
        "description": "Follow-up due notifications.",
    },
    {
        "id": "system:work_no_next_action",
        "name": "No next action",
        "category": "crm",
        "cadence": "daily",
        "cadence_label": "Daily at 08:00",
        "cron_expression": "0 8 * * *",
        "description": "Flags opportunities without a next action.",
    },
    {
        "id": "system:work_stalled_opportunity",
        "name": "Stalled opportunity",
        "category": "crm",
        "cadence": "daily",
        "cadence_label": "Daily at 09:00",
        "cron_expression": "0 9 * * *",
        "description": "Flags stalled sales opportunities.",
    },
    {
        "id": "system:sales_expire_proposals",
        "name": "Expire proposals",
        "category": "crm",
        "cadence": "hourly",
        "cadence_label": "Hourly at :50",
        "cron_expression": "50 * * * *",
        "description": "Expires proposals past their validity window.",
    },
    {
        "id": "system:sales_proposal_expiring_reminders",
        "name": "Proposal expiring reminders",
        "category": "notifications",
        "cadence": "daily",
        "cadence_label": "Daily at 08:30",
        "cron_expression": "30 8 * * *",
        "description": "Reminds owners of proposals nearing expiry.",
    },
]

# Future catalog placeholders — honest empty states, not fake engines.
CATALOG_PLACEHOLDERS: list[dict[str, Any]] = [
    {
        "id": "catalog:crm:lead-assignment",
        "name": "Lead auto-assignment",
        "category": "crm",
        "trigger": "manual",
        "description": "Planned CRM workflow for round-robin lead assignment.",
    },
    {
        "id": "catalog:investor:commitment-reminder",
        "name": "Investor commitment reminder",
        "category": "investor",
        "trigger": "scheduled",
        "description": "Planned investor relations commitment follow-up workflow.",
    },
    {
        "id": "catalog:finance:payment-reconciliation",
        "name": "Payment reconciliation alert",
        "category": "finance",
        "trigger": "scheduled",
        "description": "Planned finance reconciliation notification workflow.",
    },
    {
        "id": "catalog:projects:milestone-notify",
        "name": "Project milestone notify",
        "category": "projects",
        "trigger": "webhook",
        "description": "Planned project milestone stakeholder notification.",
    },
    {
        "id": "catalog:website:form-to-crm",
        "name": "Website form to CRM",
        "category": "website",
        "trigger": "webhook",
        "description": "Planned public-site form capture orchestration (see Marketing lead capture).",
    },
    {
        "id": "catalog:ai:document-summary",
        "name": "AI document summary job",
        "category": "ai",
        "trigger": "manual",
        "description": "Document intelligence queue jobs are monitored separately; no AI workflow builder yet.",
    },
    {
        "id": "catalog:administration:user-provisioning",
        "name": "User provisioning hooks",
        "category": "administration",
        "trigger": "webhook",
        "description": "Planned admin provisioning hooks for external identity providers.",
    },
]

CATEGORIES = [
    "crm",
    "marketing",
    "investor",
    "finance",
    "projects",
    "website",
    "ai",
    "notifications",
    "administration",
]


def compute_pages(total: int, page_size: int) -> int:
    if total <= 0:
        return 0
    return int(math.ceil(total / page_size))


def _probe_redis() -> tuple[bool, int | None, str]:
    settings = get_settings()
    try:
        from redis import Redis

        client = Redis.from_url(settings.redis_url, socket_connect_timeout=1.5, socket_timeout=1.5)
        client.ping()
        # ARQ default queue key
        size = client.llen("arq:queue")
        client.close()
        return True, int(size), "Redis connected."
    except Exception as exc:  # noqa: BLE001 — surface honest unavailable state
        return False, None, f"Redis unavailable: {exc.__class__.__name__}"


def get_queue_health() -> dict[str, Any]:
    connected, size, message = _probe_redis()
    return {
        "available": connected,
        "redis_connected": connected,
        "queue_size": size,
        "worker_registered": True,
        "message": message if connected else f"{message}. Queue depth unknown until Redis is reachable.",
        "jobs": [
            {"name": job["name"], "id": job["id"], "cadence_label": job["cadence_label"]}
            for job in ARQ_SCHEDULED_JOBS
        ],
    }


def _success_rate(completed: int, failed: int) -> tuple[float | None, bool]:
    denom = completed + failed
    if denom <= 0:
        return None, False
    return round((completed / denom) * 100, 1), True


def _trigger_from_workflow(workflow: MarketingAutomationWorkflow) -> str | None:
    trigger = workflow.trigger_json or {}
    if isinstance(trigger, dict):
        return trigger.get("type")
    return None


def _marketing_workflow_summary(
    workflow: MarketingAutomationWorkflow,
    *,
    completed: int = 0,
    failed: int = 0,
) -> dict[str, Any]:
    rate, available = _success_rate(completed, failed)
    trigger = _trigger_from_workflow(workflow)
    return {
        "id": str(workflow.id),
        "name": workflow.name,
        "category": "marketing",
        "source": "marketing_automation",
        "status": workflow.status.value,
        "trigger": trigger,
        "trigger_label": trigger,
        "last_run_at": workflow.last_run_at,
        "next_run_at": None,
        "next_run_label": "Unavailable" if trigger != "scheduled" else "Schedule not computed",
        "success_rate": rate,
        "success_rate_available": available,
        "execution_count": workflow.execution_count,
        "description": workflow.description,
        "manage_href": f"/workspaces/marketing/automations/{workflow.id}",
        "is_placeholder": False,
    }


def _system_job_summary(job: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": job["id"],
        "name": job["name"],
        "category": job["category"],
        "source": "arq_cron",
        "status": "scheduled",
        "trigger": "scheduled",
        "trigger_label": job["cadence_label"],
        "last_run_at": None,
        "next_run_at": None,
        "next_run_label": job["cadence_label"],
        "success_rate": None,
        "success_rate_available": False,
        "execution_count": 0,
        "description": job.get("description"),
        "manage_href": None,
        "is_placeholder": False,
    }


def _placeholder_summary(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": item["id"],
        "name": item["name"],
        "category": item["category"],
        "source": "catalog_placeholder",
        "status": "unavailable",
        "trigger": item.get("trigger"),
        "trigger_label": item.get("trigger"),
        "last_run_at": None,
        "next_run_at": None,
        "next_run_label": "Not scheduled",
        "success_rate": None,
        "success_rate_available": False,
        "execution_count": 0,
        "description": item.get("description"),
        "manage_href": None,
        "is_placeholder": True,
    }


def _execution_counts_by_workflow(db: Session) -> dict[UUID, dict[str, int]]:
    rows = db.execute(
        select(
            MarketingAutomationExecution.workflow_id,
            MarketingAutomationExecution.status,
            func.count(),
        ).group_by(MarketingAutomationExecution.workflow_id, MarketingAutomationExecution.status)
    ).all()
    result: dict[UUID, dict[str, int]] = {}
    for workflow_id, status, count in rows:
        bucket = result.setdefault(workflow_id, {"completed": 0, "failed": 0})
        if status == MarketingAutomationExecutionStatus.COMPLETED:
            bucket["completed"] = int(count)
        elif status == MarketingAutomationExecutionStatus.FAILED:
            bucket["failed"] = int(count)
    return result


def list_workflows(
    db: Session,
    *,
    page: int = 1,
    page_size: int = 50,
    category: str | None = None,
    search: str | None = None,
    include_placeholders: bool = True,
) -> tuple[list[dict[str, Any]], int]:
    counts = _execution_counts_by_workflow(db)
    marketing_rows = db.scalars(
        select(MarketingAutomationWorkflow)
        .where(cast(MarketingAutomationWorkflow.status, String) != MarketingAutomationWorkflowStatus.ARCHIVED.value)
        .order_by(MarketingAutomationWorkflow.updated_at.desc())
    ).all()

    items: list[dict[str, Any]] = []
    for row in marketing_rows:
        c = counts.get(row.id, {"completed": 0, "failed": 0})
        items.append(_marketing_workflow_summary(row, completed=c["completed"], failed=c["failed"]))

    for job in ARQ_SCHEDULED_JOBS:
        items.append(_system_job_summary(job))

    if include_placeholders:
        for placeholder in CATALOG_PLACEHOLDERS:
            items.append(_placeholder_summary(placeholder))

    if category:
        items = [item for item in items if item["category"] == category]
    if search:
        needle = search.strip().lower()
        items = [
            item
            for item in items
            if needle in item["name"].lower()
            or needle in (item.get("description") or "").lower()
            or needle in item["id"].lower()
        ]

    total = len(items)
    start = (page - 1) * page_size
    return items[start : start + page_size], total


def get_workflow_detail(db: Session, workflow_id: str) -> dict[str, Any] | None:
    if workflow_id.startswith("system:"):
        job = next((j for j in ARQ_SCHEDULED_JOBS if j["id"] == workflow_id), None)
        if not job:
            return None
        summary = _system_job_summary(job)
        return {
            **summary,
            "timezone": "UTC",
            "steps": [
                {
                    "id": "1",
                    "type": "arq_job",
                    "label": job["name"],
                    "config": {"cron": job.get("cron_expression")},
                }
            ],
            "dependencies": ["redis", "arq_worker"],
            "conditions": [],
            "trigger_config": {"type": "scheduled", "cron": job.get("cron_expression")},
            "history": [],
            "logs": [],
            "execution_engine_available": True,
            "execution_engine_message": "ARQ worker jobs run when Redis and the worker process are up.",
            "can_retry": False,
            "can_pause": False,
            "can_resume": False,
        }

    if workflow_id.startswith("catalog:"):
        placeholder = next((p for p in CATALOG_PLACEHOLDERS if p["id"] == workflow_id), None)
        if not placeholder:
            return None
        summary = _placeholder_summary(placeholder)
        return {
            **summary,
            "timezone": None,
            "steps": [],
            "dependencies": [],
            "conditions": [],
            "trigger_config": None,
            "history": [],
            "logs": [],
            "execution_engine_available": False,
            "execution_engine_message": "This catalog entry is a placeholder. No runner is registered.",
            "can_retry": False,
            "can_pause": False,
            "can_resume": False,
        }

    try:
        uid = UUID(workflow_id)
    except ValueError:
        return None

    workflow = db.get(MarketingAutomationWorkflow, uid)
    if not workflow:
        return None

    counts = _execution_counts_by_workflow(db).get(uid, {"completed": 0, "failed": 0})
    summary = _marketing_workflow_summary(workflow, completed=counts["completed"], failed=counts["failed"])

    actions = workflow.actions_json or []
    steps = []
    for index, action in enumerate(actions if isinstance(actions, list) else []):
        if not isinstance(action, dict):
            continue
        steps.append(
            {
                "id": str(action.get("id") or index),
                "type": str(action.get("type") or "action"),
                "label": str(action.get("type") or f"Step {index + 1}"),
                "config": action.get("config") or {},
            }
        )

    executions = db.scalars(
        select(MarketingAutomationExecution)
        .where(MarketingAutomationExecution.workflow_id == uid)
        .order_by(MarketingAutomationExecution.created_at.desc())
        .limit(25)
    ).all()

    history = [_execution_item(ex, workflow.name) for ex in executions]
    logs = [
        {
            "id": str(ex.id),
            "level": "error"
            if ex.status == MarketingAutomationExecutionStatus.FAILED
            else "warning"
            if ex.status == MarketingAutomationExecutionStatus.NOT_CONNECTED
            else "info",
            "message": ex.error_message or f"Execution {ex.status.value}",
            "created_at": ex.created_at,
            "retry_count": ex.retry_count or 0,
        }
        for ex in executions
    ]

    status_val = workflow.status.value
    return {
        **summary,
        "timezone": workflow.timezone,
        "steps": steps,
        "dependencies": ["marketing_automation", "channel_providers"],
        "conditions": workflow.conditions_json or [],
        "trigger_config": workflow.trigger_json,
        "history": history,
        "logs": logs,
        "execution_engine_available": is_execution_engine_available(),
        "execution_engine_message": execution_engine_message(),
        "can_retry": False,
        "can_pause": status_val == MarketingAutomationWorkflowStatus.ACTIVE.value,
        "can_resume": status_val
        in {
            MarketingAutomationWorkflowStatus.PAUSED.value,
            MarketingAutomationWorkflowStatus.DRAFT.value,
        },
    }


def _execution_item(execution: MarketingAutomationExecution, workflow_name: str | None = None) -> dict[str, Any]:
    return {
        "id": str(execution.id),
        "workflow_id": str(execution.workflow_id),
        "workflow_name": workflow_name,
        "status": execution.status.value,
        "trigger_type": execution.trigger_type,
        "retry_count": execution.retry_count or 0,
        "duration_ms": execution.duration_ms,
        "error_message": execution.error_message,
        "started_at": execution.started_at,
        "completed_at": execution.completed_at,
        "created_at": execution.created_at,
        "category": "marketing",
    }


def list_executions(
    db: Session,
    *,
    page: int = 1,
    page_size: int = 25,
    status_filter: str | None = None,
) -> tuple[list[dict[str, Any]], int, dict[str, int]]:
    query = select(MarketingAutomationExecution)
    if status_filter:
        query = query.where(cast(MarketingAutomationExecution.status, String) == status_filter)

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.scalars(
        query.order_by(MarketingAutomationExecution.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()

    workflow_ids = {row.workflow_id for row in rows}
    names: dict[UUID, str] = {}
    if workflow_ids:
        for wf in db.scalars(
            select(MarketingAutomationWorkflow).where(MarketingAutomationWorkflow.id.in_(workflow_ids))
        ).all():
            names[wf.id] = wf.name

    status_rows = db.execute(
        select(MarketingAutomationExecution.status, func.count()).group_by(MarketingAutomationExecution.status)
    ).all()
    status_counts = {
        (status.value if hasattr(status, "value") else str(status)): int(count) for status, count in status_rows
    }

    items = [_execution_item(row, names.get(row.workflow_id)) for row in rows]
    return items, int(total), status_counts


def list_errors(
    db: Session,
    *,
    page: int = 1,
    page_size: int = 25,
) -> tuple[list[dict[str, Any]], int]:
    query = select(MarketingAutomationExecution).where(
        cast(MarketingAutomationExecution.status, String).in_(
            [
                MarketingAutomationExecutionStatus.FAILED.value,
                MarketingAutomationExecutionStatus.NOT_CONNECTED.value,
            ]
        )
    )
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.scalars(
        query.order_by(MarketingAutomationExecution.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()

    workflow_ids = {row.workflow_id for row in rows}
    names: dict[UUID, str] = {}
    if workflow_ids:
        for wf in db.scalars(
            select(MarketingAutomationWorkflow).where(MarketingAutomationWorkflow.id.in_(workflow_ids))
        ).all():
            names[wf.id] = wf.name

    items = []
    for row in rows:
        severity = "error" if row.status == MarketingAutomationExecutionStatus.FAILED else "warning"
        items.append(
            {
                "id": str(row.id),
                "workflow_id": str(row.workflow_id),
                "workflow_name": names.get(row.workflow_id),
                "time": row.created_at,
                "severity": severity,
                "message": row.error_message
                or (
                    "Execution engine not connected"
                    if row.status == MarketingAutomationExecutionStatus.NOT_CONNECTED
                    else "Execution failed"
                ),
                "retry_count": row.retry_count or 0,
                "can_retry": False,
                "status": row.status.value,
                "category": "marketing",
            }
        )
    return items, int(total)


def list_schedules(db: Session) -> list[dict[str, Any]]:
    items = [
        {
            "id": job["id"],
            "name": job["name"],
            "category": job["category"],
            "cadence": job["cadence"],
            "cadence_label": job["cadence_label"],
            "cron_expression": job.get("cron_expression"),
            "next_run_label": job["cadence_label"],
            "last_run_at": None,
            "status": "scheduled",
            "source": "arq_cron",
            "description": job.get("description"),
        }
        for job in ARQ_SCHEDULED_JOBS
    ]

    marketing_scheduled = db.scalars(
        select(MarketingAutomationWorkflow).where(
            cast(MarketingAutomationWorkflow.status, String)
            == MarketingAutomationWorkflowStatus.ACTIVE.value
        )
    ).all()
    for workflow in marketing_scheduled:
        trigger = _trigger_from_workflow(workflow)
        if trigger not in {"scheduled", "webhook", "manual"}:
            continue
        cadence = "scheduled" if trigger == "scheduled" else trigger
        items.append(
            {
                "id": str(workflow.id),
                "name": workflow.name,
                "category": "marketing",
                "cadence": cadence if cadence in {"manual", "webhook"} else "custom",
                "cadence_label": trigger or "unknown",
                "cron_expression": None,
                "next_run_label": "Unavailable — marketing execution engine not connected",
                "last_run_at": workflow.last_run_at,
                "status": workflow.status.value,
                "source": "marketing_automation",
                "description": workflow.description,
            }
        )
    return items


def _env_configured(*keys: str) -> bool:
    return any(bool(os.getenv(key)) for key in keys)


def list_integrations() -> list[dict[str, Any]]:
    flags = get_feature_flags()
    settings = get_settings()

    openai_configured = bool(settings.ai_api_key) or _env_configured("OPENAI_API_KEY")
    n8n_enabled = bool(flags.n8n_automation)

    catalog = [
        {
            "id": "n8n",
            "name": "n8n",
            "feature_flag": "FEATURE_N8N_AUTOMATION",
            "env_keys": ["N8N_BASE_URL"],
            "configured": n8n_enabled and _env_configured("N8N_BASE_URL"),
            "enabled_flag": n8n_enabled,
            "notes": "Sidecar available in Compose; domain event bridge not wired.",
            "href": None,
        },
        {
            "id": "openai",
            "name": "OpenAI",
            "feature_flag": "FEATURE_EXTERNAL_AI",
            "env_keys": ["AI_API_KEY", "OPENAI_API_KEY"],
            "configured": openai_configured,
            "enabled_flag": bool(flags.external_ai) or openai_configured,
            "notes": "Uses AI_PROVIDER / AI_API_KEY when external AI is enabled.",
            "href": "/dashboard/ai/settings",
        },
        {
            "id": "email",
            "name": "Email",
            "feature_flag": None,
            "env_keys": ["SMTP_HOST", "EMAIL_PROVIDER_API_KEY"],
            "configured": _env_configured("SMTP_HOST", "EMAIL_PROVIDER_API_KEY"),
            "enabled_flag": True,
            "notes": "Marketing email channel APIs exist; automation actions are not connected.",
            "href": "/workspaces/marketing/email",
        },
        {
            "id": "google",
            "name": "Google",
            "feature_flag": None,
            "env_keys": ["GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET"],
            "configured": _env_configured("GOOGLE_CLIENT_ID"),
            "enabled_flag": _env_configured("GOOGLE_CLIENT_ID"),
            "notes": "Placeholder — no Google integration runner registered.",
            "href": None,
        },
        {
            "id": "slack",
            "name": "Slack",
            "feature_flag": None,
            "env_keys": ["SLACK_BOT_TOKEN", "SLACK_WEBHOOK_URL"],
            "configured": _env_configured("SLACK_BOT_TOKEN", "SLACK_WEBHOOK_URL"),
            "enabled_flag": _env_configured("SLACK_BOT_TOKEN", "SLACK_WEBHOOK_URL"),
            "notes": "Placeholder — notifications do not fan out to Slack yet.",
            "href": None,
        },
        {
            "id": "whatsapp",
            "name": "WhatsApp",
            "feature_flag": None,
            "env_keys": ["WHATSAPP_API_TOKEN", "META_WHATSAPP_TOKEN"],
            "configured": _env_configured("WHATSAPP_API_TOKEN", "META_WHATSAPP_TOKEN"),
            "enabled_flag": True,
            "notes": "Marketing WhatsApp APIs exist; automation send actions are not connected.",
            "href": "/workspaces/marketing/whatsapp",
        },
        {
            "id": "meta",
            "name": "Meta",
            "feature_flag": None,
            "env_keys": ["META_ACCESS_TOKEN", "META_APP_ID"],
            "configured": _env_configured("META_ACCESS_TOKEN", "META_APP_ID"),
            "enabled_flag": _env_configured("META_ACCESS_TOKEN", "META_APP_ID"),
            "notes": "Placeholder for ads / WhatsApp Business integrations.",
            "href": None,
        },
        {
            "id": "linkedin",
            "name": "LinkedIn",
            "feature_flag": None,
            "env_keys": ["LINKEDIN_ACCESS_TOKEN", "LINKEDIN_CLIENT_ID"],
            "configured": _env_configured("LINKEDIN_ACCESS_TOKEN", "LINKEDIN_CLIENT_ID"),
            "enabled_flag": _env_configured("LINKEDIN_ACCESS_TOKEN", "LINKEDIN_CLIENT_ID"),
            "notes": "Placeholder — no LinkedIn publisher registered.",
            "href": None,
        },
        {
            "id": "stripe",
            "name": "Stripe",
            "feature_flag": None,
            "env_keys": ["STRIPE_SECRET_KEY", "STRIPE_WEBHOOK_SECRET"],
            "configured": _env_configured("STRIPE_SECRET_KEY"),
            "enabled_flag": _env_configured("STRIPE_SECRET_KEY"),
            "notes": "Placeholder — payment webhooks not wired to automation center.",
            "href": None,
        },
    ]

    items = []
    for entry in catalog:
        configured = bool(entry["configured"])
        enabled = bool(entry["enabled_flag"])
        if configured and enabled:
            status = "connected" if entry["id"] != "n8n" or n8n_enabled else "configured"
            if entry["id"] == "n8n" and not n8n_enabled:
                status = "disabled"
            elif entry["id"] == "n8n" and n8n_enabled and not configured:
                status = "configured"
            elif entry["id"] == "n8n" and n8n_enabled and configured:
                status = "configured"  # bridge not wired — honest
        elif configured:
            status = "configured"
        elif entry["feature_flag"] and not enabled:
            status = "disabled"
        else:
            status = "unavailable"

        # n8n special-case: feature off => disabled; on but no bridge => configured
        if entry["id"] == "n8n":
            if not n8n_enabled:
                status = "disabled"
            elif configured:
                status = "configured"
            else:
                status = "unavailable"

        items.append(
            {
                "id": entry["id"],
                "name": entry["name"],
                "status": status,
                "status_label": status,
                "configured": configured,
                "feature_flag": entry["feature_flag"],
                "env_keys": entry["env_keys"],
                "notes": entry["notes"],
                "href": entry["href"],
            }
        )
    return items


def list_audit(
    db: Session,
    *,
    page: int = 1,
    page_size: int = 25,
) -> tuple[list[dict[str, Any]], int]:
    query = select(ActivityLog).where(ActivityLog.entity_type == ActivityEntityType.MARKETING_AUTOMATION)
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.scalars(
        query.order_by(ActivityLog.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    ).all()

    items = []
    for row in rows:
        meta = row.metadata_json or {}
        items.append(
            {
                "id": row.id,
                "action": row.action.value if hasattr(row.action, "value") else str(row.action),
                "entity_type": row.entity_type.value
                if hasattr(row.entity_type, "value")
                else str(row.entity_type),
                "entity_id": row.entity_id,
                "entity_label": meta.get("name") or meta.get("entity_label"),
                "description_key": row.description_key,
                "actor_name": row.actor_name,
                "created_at": row.created_at,
                "metadata": meta,
            }
        )
    return items, int(total)


def get_system_health(db: Session) -> dict[str, Any]:
    queue = get_queue_health()
    status_rows = db.execute(
        select(MarketingAutomationExecution.status, func.count()).group_by(MarketingAutomationExecution.status)
    ).all()
    counts = {status.value: int(count) for status, count in status_rows}

    avg_duration = db.scalar(
        select(func.avg(MarketingAutomationExecution.duration_ms)).where(
            MarketingAutomationExecution.duration_ms.is_not(None)
        )
    )
    last_execution = db.scalar(select(func.max(MarketingAutomationExecution.created_at)))

    workflow_total = db.scalar(select(func.count()).select_from(MarketingAutomationWorkflow)) or 0
    workflow_active = (
        db.scalar(
            select(func.count()).where(
                cast(MarketingAutomationWorkflow.status, String)
                == MarketingAutomationWorkflowStatus.ACTIVE.value
            )
        )
        or 0
    )

    engine_ok = is_execution_engine_available()
    redis_ok = queue["redis_connected"]
    if engine_ok and redis_ok:
        availability = "available"
    elif redis_ok:
        availability = "degraded"
    else:
        availability = "unavailable"

    return {
        "running_count": counts.get("running", 0),
        "failed_count": counts.get("failed", 0),
        "queued_count": counts.get("queued", 0),
        "completed_count": counts.get("completed", 0),
        "average_runtime_ms": int(avg_duration) if avg_duration is not None else None,
        "queue_size": queue["queue_size"],
        "queue_available": queue["available"],
        "last_execution_at": last_execution,
        "availability": availability,
        "execution_engine_available": engine_ok,
        "execution_engine_message": execution_engine_message(),
        "workflow_total": int(workflow_total) + len(ARQ_SCHEDULED_JOBS),
        "workflow_active": int(workflow_active) + len(ARQ_SCHEDULED_JOBS),
    }


def get_overview(db: Session) -> dict[str, Any]:
    health = get_system_health(db)
    queue_health = get_queue_health()
    _, _, status_counts = list_executions(db, page=1, page_size=1)
    workflows, _ = list_workflows(db, page=1, page_size=8, include_placeholders=False)
    errors, _ = list_errors(db, page=1, page_size=5)
    executions, _, _ = list_executions(db, page=1, page_size=8)
    schedules = list_schedules(db)[:8]
    ai_workflows = [w for w in workflows if w["category"] == "ai"]
    if not ai_workflows:
        ai_workflows = [_placeholder_summary(p) for p in CATALOG_PLACEHOLDERS if p["category"] == "ai"]
    integrations = list_integrations()

    workflow_status = [
        {"status": key, "count": value}
        for key, value in sorted(status_counts.items(), key=lambda pair: pair[0])
    ]

    return {
        "health": health,
        "workflow_status": workflow_status,
        "recent_failures": errors,
        "recent_executions": executions,
        "scheduled_jobs": schedules,
        "ai_workflows": ai_workflows,
        "integrations": integrations,
        "queue_health": queue_health,
        "generated_at": datetime.now(UTC),
    }
