import hashlib
import hmac
import secrets

from workbench.review import Forbidden
from workbench.store import connection


def password_hash(password: str, salt: str) -> str:
    return hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=16384, r=8, p=1).hex()


def seed() -> None:
    with connection() as conn:
        for name, organization, role in [
            ("ana", "aurora", "reviewer"),
            ("viewer", "aurora", "viewer"),
            ("cedro", "cedro", "reviewer"),
        ]:
            salt = secrets.token_hex(16)
            conn.execute(
                "INSERT INTO principals(id,organization,role,password_salt,password_hash) "
                "VALUES (%s,%s,%s,%s,%s) ON CONFLICT(id) DO UPDATE SET "
                "password_salt=excluded.password_salt,password_hash=excluded.password_hash,"
                "active=true,role=excluded.role",
                (name, organization, role, salt, password_hash("Synthetic-Test-Password", salt)),
            )


def login(principal_id: str, password: str) -> str:
    with connection() as conn:
        budget = conn.execute(
            "INSERT INTO login_budgets(principal_id,attempts) VALUES (%s,1) "
            "ON CONFLICT(principal_id) DO UPDATE SET attempts=CASE WHEN "
            "login_budgets.window_start < now()-interval '15 minutes' THEN 1 "
            "ELSE login_budgets.attempts+1 END, window_start=CASE WHEN "
            "login_budgets.window_start < now()-interval '15 minutes' THEN now() "
            "ELSE login_budgets.window_start END RETURNING attempts",
            (principal_id,),
        ).fetchone()
    if not budget or budget["attempts"] > 20:
        raise Forbidden("Login budget exhausted")
    with connection() as conn:
        row = conn.execute("SELECT * FROM principals WHERE id=%s", (principal_id,)).fetchone()
        if (
            not row
            or not row["active"]
            or not row["password_salt"]
            or not hmac.compare_digest(
                password_hash(password, row["password_salt"]), row["password_hash"]
            )
        ):
            raise Forbidden("Invalid credentials")
        token = secrets.token_urlsafe(32)
        conn.execute(
            "INSERT INTO sessions(token_hash,principal_id) VALUES (%s,%s)",
            (hashlib.sha256(token.encode()).hexdigest(), principal_id),
        )
        return token


def identify(token: str) -> str:
    with connection() as conn:
        row = conn.execute(
            "SELECT principal_id FROM sessions JOIN principals ON principals.id=principal_id "
            "WHERE token_hash=%s AND expires_at>now() AND active",
            (hashlib.sha256(token.encode()).hexdigest(),),
        ).fetchone()
        if not row:
            raise Forbidden("Session expired or revoked")
        return str(row["principal_id"])


if __name__ == "__main__":
    seed()
