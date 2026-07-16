"""Work item activity field tracking."""

WORK_ITEM_ACTIVITY_FIELDS = (
    "title",
    "description",
    "work_item_type",
    "status",
    "priority",
    "assigned_user_id",
    "due_at",
    "start_at",
    "is_private",
    "outcome",
    "next_action_type",
    "next_action_date",
)

WORK_TYPE_TO_OPPORTUNITY_ACTION = {
    "call": "call",
    "meeting": "meeting",
    "follow_up": "call",
    "site_visit": "site_visit",
    "proposal_follow_up": "proposal",
    "reservation_follow_up": "reservation_follow_up",
    "deposit_follow_up": "deposit_follow_up",
    "contract_follow_up": "contract_follow_up",
    "closing_follow_up": "closing_follow_up",
}
