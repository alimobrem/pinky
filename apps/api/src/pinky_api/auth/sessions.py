"""Server-side session management with Redis + Postgres audit log."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from pinky_api.security.crypto import generate_csrf_token, generate_session_token, hash_token


@dataclass
class SessionData:
    session_id: str
    principal_id: str
    token_hash: str
    csrf_token: str
    idle_expires_at: datetime
    absolute_expires_at: datetime
    created_at: datetime


class SessionManager:
    def __init__(self, idle_timeout_minutes: int = 30, absolute_timeout_hours: int = 8) -> None:
        self.idle_timeout = timedelta(minutes=idle_timeout_minutes)
        self.absolute_timeout = timedelta(hours=absolute_timeout_hours)

    def create_session(self, principal_id: str) -> tuple[str, SessionData]:
        now = datetime.now(UTC)
        token = generate_session_token()
        csrf = generate_csrf_token()

        session = SessionData(
            session_id="",
            principal_id=principal_id,
            token_hash=hash_token(token),
            csrf_token=csrf,
            idle_expires_at=now + self.idle_timeout,
            absolute_expires_at=now + self.absolute_timeout,
            created_at=now,
        )
        return token, session

    def is_valid(self, session: SessionData) -> bool:
        now = datetime.now(UTC)
        if now > session.absolute_expires_at:
            return False
        if now > session.idle_expires_at:
            return False
        return True

    def refresh_idle(self, session: SessionData) -> SessionData:
        now = datetime.now(UTC)
        new_idle = now + self.idle_timeout
        if new_idle > session.absolute_expires_at:
            new_idle = session.absolute_expires_at
        return SessionData(
            session_id=session.session_id,
            principal_id=session.principal_id,
            token_hash=session.token_hash,
            csrf_token=session.csrf_token,
            idle_expires_at=new_idle,
            absolute_expires_at=session.absolute_expires_at,
            created_at=session.created_at,
        )
