from __future__ import annotations

import asyncio
import logging
import re
from typing import Optional
from email_validator import EmailNotValidError, validate_email

from app.core.config import settings
from app.core.exceptions import BadRequestException

logger = logging.getLogger(__name__)

TEST_DOMAINS = {
    "example.com",
    "example.org",
    "example.net",
    "genz.media",
    "test.com",
    "localhost",
    "local",
}


async def resolve_mx_host(domain: str) -> Optional[str]:
    """
    Resolve the primary Mail Exchange (MX) hostname for a domain.
    """
    try:
        import dns.resolver
        answers = await asyncio.to_thread(dns.resolver.resolve, domain, "MX")
        mx_records = sorted([(r.preference, str(r.exchange).rstrip(".")) for r in answers], key=lambda x: x[0])
        if mx_records:
            return mx_records[0][1]
    except Exception as exc:
        logger.debug("[EmailVerifier] DNS MX query failed for %s: %s", domain, exc)
    return None


async def check_smtp_mailbox_exists(mx_host: str, email: str, timeout: float = 4.0) -> tuple[bool, Optional[str]]:
    """
    Perform a direct SMTP handshake (RCPT TO) with the destination MX host.
    Returns (is_valid, error_reason).
    """
    reader = None
    writer = None
    try:
        connect_task = asyncio.open_connection(mx_host, 25)
        reader, writer = await asyncio.wait_for(connect_task, timeout=timeout)

        # 1. Read greeting banner
        greeting = await asyncio.wait_for(reader.readline(), timeout=timeout)
        if not greeting.startswith(b"220"):
            return True, None  # Non-standard greeting, proceed gracefully

        # 2. Send EHLO
        writer.write(b"EHLO genzmedia.app\r\n")
        await writer.drain()

        while True:
            line = await asyncio.wait_for(reader.readline(), timeout=timeout)
            if not line or line[3:4] == b" ":
                break

        # 3. Send MAIL FROM
        writer.write(b"MAIL FROM:<noreply@genzmedia.app>\r\n")
        await writer.drain()
        mail_resp = await asyncio.wait_for(reader.readline(), timeout=timeout)
        if not (mail_resp.startswith(b"250") or mail_resp.startswith(b"200")):
            return True, None

        # 4. Send RCPT TO
        writer.write(f"RCPT TO:<{email}>\r\n".encode("utf-8"))
        await writer.drain()
        rcpt_resp = await asyncio.wait_for(reader.readline(), timeout=timeout)
        rcpt_str = rcpt_resp.decode("utf-8", errors="ignore").strip()

        # Send QUIT
        try:
            writer.write(b"QUIT\r\n")
            await writer.drain()
        except Exception:
            pass

        # 5xx responses indicate hard mailbox rejection / nonexistent user
        if rcpt_resp.startswith(b"550") or rcpt_resp.startswith(b"551") or rcpt_resp.startswith(b"553"):
            logger.warning("[EmailVerifier] Mailbox rejected by %s for %s: %s", mx_host, email, rcpt_str)
            return False, "This email address does not exist on the mail server."

        return True, None

    except (asyncio.TimeoutError, ConnectionRefusedError, OSError) as exc:
        # Port 25 blocked or remote server dropped connection; fall back gracefully
        logger.debug("[EmailVerifier] SMTP check on %s skipped due to network/firewall: %s", mx_host, exc)
        return True, None
    except Exception as exc:
        logger.debug("[EmailVerifier] Unexpected error during SMTP handshake: %s", exc)
        return True, None
    finally:
        if writer is not None:
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass


async def verify_email_deliverability(email: str) -> str:
    """
    Validate syntax, DNS MX deliverability, and attempt direct mailbox existence check.
    Raises BadRequestException if the email is invalid or undeliverable.
    Returns normalized clean email string.
    """
    clean_email = email.lower().strip()

    # In testing environments or with mock domains, validate syntax without remote DNS queries
    is_test_env = getattr(settings, "ENVIRONMENT", "").lower() in ("testing", "test")
    domain_part = clean_email.split("@")[-1] if "@" in clean_email else ""

    if is_test_env or domain_part in TEST_DOMAINS:
        try:
            validation = validate_email(clean_email, check_deliverability=False)
            return validation.normalized
        except EmailNotValidError as exc:
            raise BadRequestException(f"Invalid email address: {str(exc)}")

    # 1. Syntax and domain MX validation
    try:
        validation = validate_email(clean_email, check_deliverability=True)
        normalized_email = validation.normalized
        domain = validation.domain
    except EmailNotValidError as exc:
        raise BadRequestException(f"Invalid email address: {str(exc)}")

    # 2. Check primary MX server
    mx_host = await resolve_mx_host(domain)
    if not mx_host:
        raise BadRequestException("The email domain does not have valid mail servers configured.")

    # 3. Direct SMTP RCPT TO mailbox check
    is_valid, error_reason = await check_smtp_mailbox_exists(mx_host, normalized_email)
    if not is_valid and error_reason:
        raise BadRequestException(error_reason)

    return normalized_email
