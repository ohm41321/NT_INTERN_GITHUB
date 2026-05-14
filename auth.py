import bcrypt
# Patch bcrypt to work with passlib and bcrypt >= 4.0.0
# bcrypt 4.0+ raises ValueError for passwords > 72 bytes, which breaks passlib's internal safety check.
_original_hashpw = bcrypt.hashpw

def _patched_hashpw(password, salt, *args, **kwargs):
    if len(password) > 72:
        # Truncate for passlib's check to prevent crash.
        # This effectively tells passlib that the backend behaves "correctly" (doesn't silently wrap but we handle it manually in verify_password)
        password = password[:72]
    return _original_hashpw(password, salt, *args, **kwargs)

bcrypt.hashpw = _patched_hashpw

from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    # bcrypt fails if password is longer than 72 bytes
    if len(plain.encode('utf-8')) > 72:
        return False
    return pwd_context.verify(plain, hashed)
