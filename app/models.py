from __future__ import annotations

import secrets
from datetime import UTC, datetime

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db


def utcnow() -> datetime:
    return datetime.now(UTC)


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    display_name = db.Column(db.String(120), nullable=False, default="")
    google_sub = db.Column(db.String(255), unique=True, nullable=True, index=True)
    avatar_url = db.Column(db.String(512), nullable=False, default="")
    auth_provider = db.Column(db.String(32), nullable=False, default="password")
    email_verified = db.Column(db.Boolean, nullable=False, default=False)
    default_brand_tone = db.Column(db.String(160), nullable=False, default="")
    default_content_density = db.Column(db.String(24), nullable=False, default="balanced")
    default_motion_level = db.Column(db.String(24), nullable=False, default="moderate")
    default_icon_style = db.Column(db.String(220), nullable=False, default="")
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)

    conversations = db.relationship(
        "Conversation",
        back_populates="user",
        cascade="all, delete-orphan",
        order_by="desc(Conversation.updated_at)",
    )
    onboarding = db.relationship(
        "UserOnboarding",
        back_populates="user",
        cascade="all, delete-orphan",
        uselist=False,
    )

    @staticmethod
    def make_unusable_password() -> str:
        return generate_password_hash(secrets.token_urlsafe(32))

    @property
    def is_google_linked(self) -> bool:
        return bool((self.google_sub or "").strip())

    @property
    def has_password_login(self) -> bool:
        return self.auth_provider in {"password", "google+password"}

    def set_password(self, raw_password: str) -> None:
        self.password_hash = generate_password_hash(raw_password)
        self.auth_provider = "google+password" if self.is_google_linked else "password"

    def check_password(self, raw_password: str) -> bool:
        if not self.has_password_login:
            return False
        password_hash = (self.password_hash or "").strip()
        if not password_hash:
            return False
        return check_password_hash(password_hash, raw_password)

    def sync_auth_provider(self) -> None:
        if self.is_google_linked and self.has_password_login:
            self.auth_provider = "google+password"
        elif self.is_google_linked:
            self.auth_provider = "google"
        else:
            self.auth_provider = "password"


class UserOnboarding(db.Model):
    __tablename__ = "user_onboardings"

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), primary_key=True)
    user_type = db.Column(db.String(40), nullable=True)
    discovery_source = db.Column(db.String(40), nullable=True)
    discovery_note = db.Column(db.String(220), nullable=False, default="")
    completed_at = db.Column(db.DateTime(timezone=True), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)

    user = db.relationship("User", back_populates="onboarding")


class Conversation(db.Model):
    __tablename__ = "conversations"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    title = db.Column(db.String(200), nullable=False)
    preview_id = db.Column(db.String(64), unique=True, nullable=False, index=True)
    manifest_json = db.Column(db.JSON, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow, index=True)

    user = db.relationship("User", back_populates="conversations")
    messages = db.relationship(
        "Message",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Message.created_at",
    )


class Message(db.Model):
    __tablename__ = "messages"

    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey("conversations.id"), nullable=False, index=True)
    role = db.Column(db.String(24), nullable=False)
    body = db.Column(db.Text, nullable=False)
    preview_id = db.Column(db.String(64), nullable=True, index=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, index=True)

    conversation = db.relationship("Conversation", back_populates="messages")
