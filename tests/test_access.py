import pytest

from backend.app.core.config import settings
from backend.app.services.invites import InviteStore
from backend.app.services.telegram_access import TelegramAccess


@pytest.fixture
def db(tmp_path):
    return tmp_path / "t.db"


def test_invite_lifecycle(db):
    store = InviteStore(db)
    inv = store.create("  Aliyev Vali ")
    assert inv["name"] == "Aliyev Vali" and len(inv["token"]) >= 30
    user = store.verify(inv["token"])
    assert user == {"id": inv["id"], "name": "Aliyev Vali", "session_id": f"web:{inv['id']}"}
    assert store.verify("wrong-token") is None
    assert store.verify("") is None
    # Only a hash is stored, never the token itself.
    assert inv["token"] not in db.read_bytes().decode("latin-1")
    assert store.list()[0]["last_used_at"] is not None
    assert store.revoke(inv["id"]) is True
    assert store.verify(inv["token"]) is None
    assert store.revoke(inv["id"]) is False


def test_telegram_access_flow(db, monkeypatch):
    monkeypatch.setattr(settings, "TELEGRAM_ALLOWED_USER_IDS", "111")
    access = TelegramAccess(db)
    assert access.check(111) == {"allowed": True, "status": "admin", "new_request": False}
    first = access.check(222, "@vali")
    assert first == {"allowed": False, "status": "pending", "new_request": True}
    assert access.check(222)["new_request"] is False  # asking again isn't a new request
    assert access.set_status(222, "allowed") is True
    assert access.check(222)["allowed"] is True
    assert access.set_status(222, "blocked") is True
    assert access.check(222)["allowed"] is False
    assert access.set_status(222, "nonsense") is False
    assert access.set_status(111, "blocked") is False  # admins can't be blocked
    assert [u["user_id"] for u in access.list()] == [222]
