import json
import os
import sys
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))
import fa_auth


def test_password_hash_roundtrip():
    h = fa_auth.hash_password("Secret123")
    assert h.startswith("scrypt$") and "Secret123" not in h
    assert fa_auth.verify_password("Secret123", h)
    assert not fa_auth.verify_password("secret123", h)
    assert not fa_auth.verify_password("x", "garbage")
    assert fa_auth.hash_password("Secret123") != h  # salted


def test_password_rules_and_email():
    assert fa_auth.password_problems("Secret123", "Secret123") == []
    assert fa_auth.password_problems("short1")
    assert fa_auth.password_problems("lettersonly")
    assert "both passwords to match" in fa_auth.password_problems("Secret123", "Secret124")
    assert fa_auth.valid_email(" Me@Example.co.uk ")
    assert not fa_auth.valid_email("nope@")
    assert fa_auth.normalize_email(" Me@Example.COM ") == "me@example.com"


def test_local_store_and_session_tokens(tmp_path):
    store = fa_auth.AuthStore(None, local_path=str(tmp_path / "auth.json"))
    assert not store.has_users()
    assert store.set_password("Me@Example.com", "Secret123")
    assert store.has_users()
    user = store.get_user("me@example.com")
    assert fa_auth.verify_password("Secret123", user["password_hash"])
    raw = json.loads((tmp_path / "auth.json").read_text())
    assert "Secret123" not in json.dumps(raw)

    secret = store.session_secret()
    token = fa_auth.make_session_token("me@example.com", user["password_hash"], secret)
    assert fa_auth.read_session_token(token, store) == "me@example.com"
    # tampered / expired / wrong secret
    assert fa_auth.read_session_token(token[:-2] + "00", store) is None
    old = fa_auth.make_session_token("me@example.com", user["password_hash"], secret, now=0)
    assert fa_auth.read_session_token(old, store) is None
    forged = fa_auth.make_session_token("me@example.com", user["password_hash"], "not-the-secret")
    assert fa_auth.read_session_token(forged, store) is None
    # changing the password signs out remembered devices
    store.set_password("me@example.com", "NewSecret456")
    assert fa_auth.read_session_token(token, store) is None


def test_supabase_store_uses_private_bucket():
    client = MagicMock()
    bucket = MagicMock()
    client.storage.from_.return_value = bucket
    bucket.download.side_effect = Exception("not found")
    store = fa_auth.AuthStore(client, local_path="/nonexistent/dir/auth.json")
    assert store.set_password("a@b.co", "Secret123")
    client.storage.create_bucket.assert_called_with("app_auth", options={"public": False})
    client.storage.from_.assert_called_with("app_auth")
    kwargs = bucket.upload.call_args.kwargs
    assert kwargs["path"] == "auth.json"
    assert b"a@b.co" in kwargs["file"]


def test_email_codes():
    rec = fa_auth.code_record("123456", "a@b.co", "login", now=1000)
    assert "123456" not in json.dumps(rec)
    ok, _ = fa_auth.check_code(rec, "000000", now=1001)
    assert not ok
    ok, _ = fa_auth.check_code(rec, "123 456", now=1002)
    assert ok
    rec = fa_auth.code_record("123456", "a@b.co", "login", now=1000)
    assert not fa_auth.check_code(rec, "123456", now=1000 + 11 * 60)[0]  # expired
    rec = fa_auth.code_record("123456", "a@b.co", "login", now=1000)
    for _ in range(fa_auth.CODE_MAX_ATTEMPTS):
        fa_auth.check_code(rec, "999999", now=1001)
    assert not fa_auth.check_code(rec, "123456", now=1001)[0]  # locked out
    assert len(fa_auth.new_code()) == 6


def test_send_code_email_calls_resend():
    resp = MagicMock(status=200)
    resp.__enter__.return_value = resp
    with patch("fa_auth.urllib.request.urlopen", return_value=resp) as op:
        ok, err = fa_auth.send_code_email("re_test", "FA <a@b.co>", "me@x.com", "123456", "login")
    assert ok and not err
    req = op.call_args.args[0]
    assert req.full_url == "https://api.resend.com/emails"
    assert req.headers["Authorization"] == "Bearer re_test"
    body = json.loads(req.data)
    assert body["to"] == ["me@x.com"] and "123456" in body["subject"]
    assert fa_auth.send_code_email("", "x", "y", "1", "login")[0] is False
