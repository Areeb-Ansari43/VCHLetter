"""Login, password storage, email 2FA (Resend) and remember-me cookies.

Nothing secret lives in this file:
- Passwords are stored only as salted scrypt hashes.
- The account file is kept in a *private* Supabase Storage bucket
  (`app_auth/auth.json`), falling back to a git-ignored local file when
  Supabase isn't configured (local development).
- Remember-me cookies are HMAC-signed with a random key generated at setup,
  and stop working as soon as the password changes.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import time
import urllib.error
import urllib.request

AUTH_BUCKET = "app_auth"
AUTH_OBJECT = "auth.json"
LOCAL_AUTH_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".auth_store.json")

REMEMBER_COOKIE = "fa_ibi_session"
REMEMBER_DAYS = 30
CODE_TTL_SECONDS = 10 * 60
CODE_MAX_ATTEMPTS = 5
RESEND_COOLDOWN_SECONDS = 30
MIN_PASSWORD_LENGTH = 8


# ─────────────────────────── passwords ───────────────────────────
def hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=2 ** 14, r=8, p=1, dklen=32)
    return f"scrypt${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, salt_hex, hash_hex = str(stored).split("$")
        if algo != "scrypt":
            return False
        digest = hashlib.scrypt(password.encode("utf-8"), salt=bytes.fromhex(salt_hex), n=2 ** 14, r=8, p=1, dklen=32)
        return hmac.compare_digest(digest.hex(), hash_hex)
    except Exception:
        return False


def password_problems(password: str, confirm: str | None = None) -> list[str]:
    problems = []
    if len(password or "") < MIN_PASSWORD_LENGTH:
        problems.append(f"at least {MIN_PASSWORD_LENGTH} characters")
    if not any(c.isalpha() for c in password or "") or not any(c.isdigit() for c in password or ""):
        problems.append("a mix of letters and numbers")
    if confirm is not None and password != confirm:
        problems.append("both passwords to match")
    return problems


def normalize_email(email: str) -> str:
    return str(email or "").strip().lower()


def valid_email(email: str) -> bool:
    e = normalize_email(email)
    if "@" not in e or " " in e:
        return False
    local, _, domain = e.partition("@")
    return bool(local) and "." in domain and not domain.startswith(".") and not domain.endswith(".")


# ─────────────────────────── account store ───────────────────────────
class AuthStore:
    """Reads/writes the account file in a private Supabase bucket (or locally)."""

    def __init__(self, supabase_client=None, local_path: str = LOCAL_AUTH_FILE):
        self.client = supabase_client
        self.local_path = local_path

    # -- backend helpers --
    def _ensure_bucket(self):
        try:
            self.client.storage.create_bucket(AUTH_BUCKET, options={"public": False})
        except Exception:
            pass  # already exists (or no permission — upload will tell us)

    def load(self) -> dict:
        data = None
        if self.client is not None:
            try:
                raw = self.client.storage.from_(AUTH_BUCKET).download(AUTH_OBJECT)
                data = json.loads(raw.decode("utf-8")) if raw else None
            except Exception:
                data = None
        if data is None and os.path.exists(self.local_path):
            try:
                with open(self.local_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                data = None
        if not isinstance(data, dict):
            data = {}
        data.setdefault("users", {})
        return data

    def save(self, data: dict) -> bool:
        payload = json.dumps(data, indent=2).encode("utf-8")
        saved = False
        if self.client is not None:
            self._ensure_bucket()
            try:
                self.client.storage.from_(AUTH_BUCKET).upload(
                    path=AUTH_OBJECT, file=payload,
                    file_options={"content-type": "application/json", "upsert": "true"},
                )
                saved = True
            except Exception:
                saved = False
        if not saved:
            try:
                with open(self.local_path, "wb") as f:
                    f.write(payload)
                try:
                    os.chmod(self.local_path, 0o600)
                except Exception:
                    pass
                saved = True
            except Exception:
                saved = False
        return saved

    # -- account helpers --
    def has_users(self) -> bool:
        return bool(self.load().get("users"))

    def get_user(self, email: str) -> dict | None:
        return self.load().get("users", {}).get(normalize_email(email))

    def set_password(self, email: str, password: str) -> bool:
        data = self.load()
        email = normalize_email(email)
        user = data["users"].get(email, {"created_at": int(time.time())})
        user["password_hash"] = hash_password(password)
        user["updated_at"] = int(time.time())
        data["users"][email] = user
        if not data.get("session_secret"):
            data["session_secret"] = secrets.token_hex(32)
        return self.save(data)

    def session_secret(self) -> str:
        data = self.load()
        if not data.get("session_secret"):
            data["session_secret"] = secrets.token_hex(32)
            self.save(data)
        return data["session_secret"]


# ─────────────────────────── remember-me tokens ───────────────────────────
def _password_version(password_hash: str) -> str:
    return hashlib.sha256(str(password_hash).encode()).hexdigest()[:16]


def make_session_token(email: str, password_hash: str, secret: str, days: int = REMEMBER_DAYS, now: float | None = None) -> str:
    exp = int((time.time() if now is None else now) + days * 86400)
    payload = f"{normalize_email(email)}|{exp}|{_password_version(password_hash)}"
    sig = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return base64.urlsafe_b64encode(payload.encode()).decode().rstrip("=") + "." + sig


def read_session_token(token: str, store: AuthStore, now: float | None = None) -> str | None:
    """Return the email for a valid, unexpired token whose password is unchanged."""
    try:
        body, sig = str(token or "").split(".", 1)
        payload = base64.urlsafe_b64decode(body + "=" * (-len(body) % 4)).decode()
        email, exp, pw_ver = payload.split("|")
        data = store.load()
        secret = data.get("session_secret")
        user = data.get("users", {}).get(email)
        if not secret or not user:
            return None
        expected = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, sig):
            return None
        if int(exp) < (time.time() if now is None else now):
            return None
        if pw_ver != _password_version(user.get("password_hash", "")):
            return None
        return email
    except Exception:
        return None


# ─────────────────────────── one-time email codes ───────────────────────────
def new_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def code_record(code: str, email: str, purpose: str, now: float | None = None) -> dict:
    now = time.time() if now is None else now
    salt = secrets.token_hex(8)
    return {
        "email": normalize_email(email),
        "purpose": purpose,
        "salt": salt,
        "hash": hashlib.sha256((salt + code).encode()).hexdigest(),
        "expires": now + CODE_TTL_SECONDS,
        "attempts": 0,
        "sent_at": now,
    }


def check_code(record: dict | None, code: str, now: float | None = None) -> tuple[bool, str]:
    """Validate a code. Mutates `attempts`. Returns (ok, message)."""
    if not record:
        return False, "Please request a new code."
    now = time.time() if now is None else now
    if now > record.get("expires", 0):
        return False, "That code has expired — send a new one."
    if record.get("attempts", 0) >= CODE_MAX_ATTEMPTS:
        return False, "Too many wrong codes — send a new one."
    record["attempts"] = record.get("attempts", 0) + 1
    clean = "".join(ch for ch in str(code or "") if ch.isdigit())
    digest = hashlib.sha256((record.get("salt", "") + clean).encode()).hexdigest()
    if hmac.compare_digest(digest, record.get("hash", "")):
        return True, ""
    left = CODE_MAX_ATTEMPTS - record["attempts"]
    return False, f"Incorrect code — {left} attempt{'s' if left != 1 else ''} left."


def send_code_email(api_key: str, sender: str, to_email: str, code: str, purpose: str) -> tuple[bool, str]:
    """Send the 6-digit code with Resend. Returns (ok, error_message)."""
    if not api_key:
        return False, "Email sending isn't set up yet (RESEND_API_KEY is missing from the app secrets)."
    heading = {
        "login": "Your sign-in code",
        "setup": "Confirm your email",
        "reset": "Reset your password",
    }.get(purpose, "Your verification code")
    html = f"""
    <div style="font-family:-apple-system,Segoe UI,Roboto,Arial,sans-serif;max-width:440px;margin:auto;padding:24px;color:#111">
      <div style="font-size:20px;font-weight:700;color:#ff7a59;margin-bottom:4px">FA-IBI Workspace</div>
      <div style="font-size:15px;margin-bottom:18px">{heading}</div>
      <div style="font-size:34px;font-weight:800;letter-spacing:8px;background:#fff4ec;border:1px solid #ffd9c2;
                  border-radius:10px;padding:14px 0;text-align:center;color:#111">{code}</div>
      <p style="font-size:13px;color:#555;margin-top:18px">This code expires in 10 minutes.
      If you didn't try to sign in, you can ignore this email — your password is still safe.</p>
      <p style="font-size:12px;color:#999">Virtual Car Hire · FA-IBI LTD</p>
    </div>"""
    body = json.dumps({
        "from": sender,
        "to": [to_email],
        "subject": f"{code} is your FA-IBI Workspace code",
        "html": html,
        "text": f"{heading}: {code}\nThis code expires in 10 minutes.",
    }).encode("utf-8")
    req = urllib.request.Request(
        "https://api.resend.com/emails", data=body, method="POST",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json",
                 "User-Agent": "fa-ibi-workspace/1.0"},
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            if 200 <= resp.status < 300:
                return True, ""
            return False, f"Resend returned status {resp.status}."
    except urllib.error.HTTPError as e:
        try:
            detail = json.loads(e.read().decode()).get("message", "")
        except Exception:
            detail = ""
        return False, f"Couldn't send the email ({e.code}{': ' + detail if detail else ''})."
    except Exception as e:
        return False, f"Couldn't send the email: {e}"
