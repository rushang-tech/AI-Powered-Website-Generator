from __future__ import annotations

from datetime import UTC
from typing import Any

from app.extensions import db
from app.models import Conversation, Message, User, utcnow
from app.services.contracts import ProjectManifest

VISIBLE_ROLES = {"user", "assistant"}


def _truncate(text: str, *, limit: int) -> str:
    normalized = " ".join(text.split()).strip()
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 1].rstrip() + "…"


def conversation_title_from_manifest(manifest: ProjectManifest) -> str:
    brief = manifest.brief
    for value in (brief.name, brief.goal, manifest.prompt):
        text = _truncate(str(value or ""), limit=80)
        if text:
            return text
    return "Untitled conversation"


def initial_assistant_message(manifest: ProjectManifest) -> str:
    target = manifest.brief.name or manifest.brief.goal or manifest.prompt or "this project"
    return f"Created a new workspace for {target} with three design directions ready to review."


def manifest_from_conversation(conversation: Conversation) -> ProjectManifest:
    payload = conversation.manifest_json if isinstance(conversation.manifest_json, dict) else {}
    return ProjectManifest.from_dict(payload)


def serialize_message(message: Message) -> dict[str, Any]:
    created_at = message.created_at.astimezone(UTC).isoformat() if message.created_at else ""
    return {
        "id": message.id,
        "role": message.role,
        "body": message.body,
        "preview_id": message.preview_id,
        "created_at": created_at,
    }


def serialize_conversation_summary(conversation: Conversation) -> dict[str, Any]:
    preview_path = f"/preview/{conversation.preview_id}"
    updated_at = conversation.updated_at.astimezone(UTC).isoformat() if conversation.updated_at else ""
    return {
        "id": conversation.id,
        "title": conversation.title,
        "preview_id": conversation.preview_id,
        "preview_url": preview_path,
        "updated_at": updated_at,
    }


def visible_messages(conversation: Conversation) -> list[dict[str, Any]]:
    return [serialize_message(message) for message in conversation.messages if message.role in VISIBLE_ROLES]


def history_messages(conversation: Conversation) -> list[dict[str, Any]]:
    return [serialize_message(message) for message in conversation.messages]


def list_recent_conversations(user: User, *, limit: int = 12) -> list[Conversation]:
    return (
        Conversation.query.filter_by(user_id=user.id)
        .order_by(Conversation.updated_at.desc(), Conversation.id.desc())
        .limit(limit)
        .all()
    )


def get_conversation_for_user(conversation_id: int, user: User) -> Conversation | None:
    return Conversation.query.filter_by(id=conversation_id, user_id=user.id).first()


def get_conversation_by_preview(preview_id: str, user: User) -> Conversation | None:
    return Conversation.query.filter_by(preview_id=preview_id, user_id=user.id).first()


def append_message(
    conversation: Conversation,
    *,
    role: str,
    body: str,
    preview_id: str | None = None,
    commit: bool = True,
) -> Message:
    message = Message(
        conversation=conversation,
        role=role,
        body=" ".join(body.split()).strip(),
        preview_id=preview_id,
    )
    conversation.updated_at = utcnow()
    db.session.add(message)
    db.session.add(conversation)
    if commit:
        db.session.commit()
    return message


def save_manifest(conversation: Conversation, manifest: ProjectManifest, *, commit: bool = True) -> Conversation:
    conversation.preview_id = manifest.preview_id
    if not str(conversation.title or "").strip():
        conversation.title = conversation_title_from_manifest(manifest)
    conversation.manifest_json = manifest.to_dict()
    conversation.updated_at = utcnow()
    db.session.add(conversation)
    if commit:
        db.session.commit()
    return conversation


def create_conversation(
    user: User,
    *,
    manifest: ProjectManifest,
    user_message: str,
    assistant_message: str | None = None,
) -> Conversation:
    conversation = Conversation(
        user=user,
        title=conversation_title_from_manifest(manifest),
        preview_id=manifest.preview_id,
        manifest_json=manifest.to_dict(),
    )
    db.session.add(conversation)
    db.session.flush()

    append_message(conversation, role="user", body=user_message, preview_id=manifest.preview_id, commit=False)
    append_message(
        conversation,
        role="assistant",
        body=assistant_message or initial_assistant_message(manifest),
        preview_id=manifest.preview_id,
        commit=False,
    )
    db.session.commit()
    return conversation


def rename_conversation(conversation: Conversation, title: str) -> Conversation:
    cleaned = _truncate(title, limit=120) or conversation.title
    conversation.title = cleaned
    conversation.updated_at = utcnow()
    db.session.add(conversation)
    db.session.commit()
    return conversation


def delete_conversation(conversation: Conversation) -> None:
    db.session.delete(conversation)
    db.session.commit()


def record_system_event(conversation: Conversation, description: str) -> Message:
    return append_message(conversation, role="system", body=description, preview_id=conversation.preview_id)
