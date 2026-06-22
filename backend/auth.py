import os

import bcrypt
from fastapi import Cookie, Depends, HTTPException
from itsdangerous import BadSignature, URLSafeSerializer

_signer = URLSafeSerializer(
    os.getenv("SECRET_KEY", "dev-secret-key-change-in-production"),
    salt="session",
)


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())


def create_session_token(user_id: int) -> str:
    return _signer.dumps(user_id)


def _decode_session_token(token: str) -> int:
    try:
        return _signer.loads(token)
    except BadSignature:
        raise HTTPException(status_code=401, detail="Invalid session")


def get_current_user_id(session: str | None = Cookie(default=None)) -> int:
    if session is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return _decode_session_token(session)
