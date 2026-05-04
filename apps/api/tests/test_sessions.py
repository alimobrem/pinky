from datetime import UTC, datetime, timedelta

from pinky_api.auth.sessions import SessionData, SessionManager


def test_create_session() -> None:
    mgr = SessionManager(idle_timeout_minutes=30, absolute_timeout_hours=8)
    token, session = mgr.create_session("principal-123")

    assert len(token) > 32
    assert session.principal_id == "principal-123"
    assert session.csrf_token
    assert session.idle_expires_at > datetime.now(UTC)
    assert session.absolute_expires_at > session.idle_expires_at


def test_session_valid_when_fresh() -> None:
    mgr = SessionManager()
    _, session = mgr.create_session("p1")
    assert mgr.is_valid(session)


def test_session_invalid_after_idle_expiry() -> None:
    mgr = SessionManager(idle_timeout_minutes=30)
    _, session = mgr.create_session("p1")
    expired = SessionData(
        session_id=session.session_id,
        principal_id=session.principal_id,
        token_hash=session.token_hash,
        csrf_token=session.csrf_token,
        idle_expires_at=datetime.now(UTC) - timedelta(minutes=1),
        absolute_expires_at=session.absolute_expires_at,
        created_at=session.created_at,
    )
    assert not mgr.is_valid(expired)


def test_session_invalid_after_absolute_expiry() -> None:
    mgr = SessionManager()
    _, session = mgr.create_session("p1")
    expired = SessionData(
        session_id=session.session_id,
        principal_id=session.principal_id,
        token_hash=session.token_hash,
        csrf_token=session.csrf_token,
        idle_expires_at=datetime.now(UTC) + timedelta(hours=1),
        absolute_expires_at=datetime.now(UTC) - timedelta(minutes=1),
        created_at=session.created_at,
    )
    assert not mgr.is_valid(expired)


def test_refresh_idle_extends_timeout() -> None:
    mgr = SessionManager(idle_timeout_minutes=30)
    _, session = mgr.create_session("p1")
    original_idle = session.idle_expires_at
    refreshed = mgr.refresh_idle(session)
    assert refreshed.idle_expires_at >= original_idle


def test_refresh_idle_capped_by_absolute() -> None:
    mgr = SessionManager(idle_timeout_minutes=30, absolute_timeout_hours=8)
    _, session = mgr.create_session("p1")
    near_absolute = SessionData(
        session_id=session.session_id,
        principal_id=session.principal_id,
        token_hash=session.token_hash,
        csrf_token=session.csrf_token,
        idle_expires_at=session.absolute_expires_at - timedelta(minutes=5),
        absolute_expires_at=session.absolute_expires_at,
        created_at=session.created_at,
    )
    refreshed = mgr.refresh_idle(near_absolute)
    assert refreshed.idle_expires_at <= session.absolute_expires_at
