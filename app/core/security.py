from pwdlib import PasswordHash

password_hash = PasswordHash.recommended()


def get_password_hash(password: str) -> str:
    """Hash a plaintext password using Argon2."""
    return password_hash.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against a stored hash."""
    return password_hash.verify(plain_password, hashed_password)
