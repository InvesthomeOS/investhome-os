"""Short conversation memory for Project Assistant follow-ups (no long-term agent)."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from uuid import UUID, uuid4

_MAX_TURNS = 6
_TTL_SECONDS = 60 * 60  # 1 hour
_MAX_CONVERSATIONS = 500


@dataclass
class ConversationTurn:
    question: str
    answer: str
    created_at: float = field(default_factory=time.time)


@dataclass
class ConversationState:
    id: UUID
    turns: list[ConversationTurn] = field(default_factory=list)
    updated_at: float = field(default_factory=time.time)


_lock = threading.Lock()
_store: dict[UUID, ConversationState] = {}


def _purge_locked(now: float) -> None:
    stale = [cid for cid, st in _store.items() if now - st.updated_at > _TTL_SECONDS]
    for cid in stale:
        _store.pop(cid, None)
    if len(_store) <= _MAX_CONVERSATIONS:
        return
    # Evict oldest
    ordered = sorted(_store.items(), key=lambda kv: kv[1].updated_at)
    overflow = len(_store) - _MAX_CONVERSATIONS
    for cid, _ in ordered[:overflow]:
        _store.pop(cid, None)


def get_or_create_conversation(conversation_id: UUID | None) -> ConversationState:
    with _lock:
        now = time.time()
        _purge_locked(now)
        if conversation_id is not None and conversation_id in _store:
            return _store[conversation_id]
        cid = conversation_id or uuid4()
        state = ConversationState(id=cid)
        _store[cid] = state
        return state


def get_history(conversation_id: UUID | None) -> list[dict[str, str]]:
    if conversation_id is None:
        return []
    with _lock:
        state = _store.get(conversation_id)
        if state is None:
            return []
        return [{"question": t.question, "answer": t.answer} for t in state.turns]


def append_turn(conversation_id: UUID, *, question: str, answer: str) -> None:
    with _lock:
        now = time.time()
        _purge_locked(now)
        state = _store.get(conversation_id)
        if state is None:
            state = ConversationState(id=conversation_id)
            _store[conversation_id] = state
        state.turns.append(ConversationTurn(question=question, answer=answer))
        if len(state.turns) > _MAX_TURNS:
            state.turns = state.turns[-_MAX_TURNS:]
        state.updated_at = now


def clear_conversations_for_tests() -> None:
    with _lock:
        _store.clear()
