from __future__ import annotations

import logging
from email.message import EmailMessage
from typing import Optional
import aiosmtplib

from app.core.config import settings

logger = logging.getLogger(__name__)


async def send_email(
    to_email: str,
    subject: str,
    html_content: str,
    text_content: Optional[str] = None,
) -> bool:
    """
    Send an asynchronous email via SMTP using aiosmtplib.
    
    Supports local development (Mailpit/MailHog with no auth) as well as
    production SMTP servers (TLS/STARTTLS with authentication).
    """
    if not settings.SMTP_HOST:
        logger.warning("[EmailService] SMTP_HOST is not configured. Email to %s skipped.", to_email)
        return False

    message = EmailMessage()
    message["From"] = f"{settings.EMAILS_FROM_NAME} <{settings.EMAILS_FROM_EMAIL}>"
    message["To"] = to_email
    message["Subject"] = subject

    if text_content:
        message.set_content(text_content)
        message.add_alternative(html_content, subtype="html")
    else:
        message.set_content(html_content, subtype="html")

    try:
        username = settings.SMTP_USER if settings.SMTP_USER else None
        password = settings.SMTP_PASSWORD if settings.SMTP_PASSWORD else None

        await aiosmtplib.send(
            message,
            hostname=settings.SMTP_HOST,
            port=settings.SMTP_PORT,
            username=username,
            password=password,
            use_tls=settings.SMTP_USE_SSL,
            start_tls=settings.SMTP_STARTTLS,
            timeout=10,
        )
        logger.info("[EmailService] Email successfully sent to %s (subject: '%s')", to_email, subject)
        return True
    except Exception as exc:
        logger.error("[EmailService] Failed to send email to %s: %s", to_email, exc)
        return False


async def send_password_reset_email(
    to_email: str,
    reset_token: str,
    username: Optional[str] = None,
) -> bool:
    """
    Compose and send a password configuration / reset email with reset token link.
    """
    greeting_name = f"Hi {username}," if username else "Hello,"
    reset_url = f"{settings.FRONTEND_URL}/reset-password?token={reset_token}"
    subject = "Reset Your Password - GenZ Media"

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{subject}</title>
    </head>
    <body style="margin: 0; padding: 0; background-color: #f8fafc; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #1e293b;">
        <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background-color: #f8fafc; padding: 40px 20px;">
            <tr>
                <td align="center">
                    <table role="presentation" width="100%" style="max-width: 540px; background-color: #ffffff; border-radius: 16px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03); overflow: hidden; border: 1px solid #e2e8f0;">
                        <!-- Header -->
                        <tr>
                            <td style="padding: 32px 32px 20px; text-align: center; background: linear-gradient(135deg, #6366F1 0%, #A855F7 100%);">
                                <h1 style="margin: 0; color: #ffffff; font-size: 24px; font-weight: 700; letter-spacing: -0.5px;">GenZ Media</h1>
                            </td>
                        </tr>
                        <!-- Content -->
                        <tr>
                            <td style="padding: 32px;">
                                <h2 style="margin: 0 0 16px; color: #0f172a; font-size: 20px; font-weight: 600;">{greeting_name}</h2>
                                <p style="margin: 0 0 20px; color: #475569; font-size: 15px; line-height: 1.6;">
                                    We received a request to configure or reset your password for your GenZ Media account.
                                </p>
                                <div style="text-align: center; margin: 32px 0;">
                                    <a href="{reset_url}" style="background: linear-gradient(135deg, #6366F1 0%, #8B5CF6 100%); color: #ffffff; font-size: 15px; font-weight: 600; text-decoration: none; padding: 14px 32px; border-radius: 10px; display: inline-block; box-shadow: 0 4px 12px rgba(99, 102, 241, 0.35);">
                                        Reset Password
                                    </a>
                                </div>
                                <p style="margin: 0 0 12px; color: #64748b; font-size: 13px;">
                                    If button above does not work, copy and paste this link into your browser:
                                </p>
                                <p style="margin: 0 0 24px; background-color: #f1f5f9; padding: 12px; border-radius: 8px; font-size: 12px; word-break: break-all; color: #475569; font-family: monospace;">
                                    <a href="{reset_url}" style="color: #6366f1; text-decoration: underline;">{reset_url}</a>
                                </p>
                                <div style="border-top: 1px solid #f1f5f9; padding-top: 20px; margin-top: 24px;">
                                    <p style="margin: 0; color: #94a3b8; font-size: 12px; line-height: 1.5;">
                                        ⏳ This reset link is valid for <strong>{settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES} minutes</strong>.
                                    </p>
                                    <p style="margin: 6px 0 0; color: #94a3b8; font-size: 12px; line-height: 1.5;">
                                        If you didn't request a password reset, you can safely ignore this email.
                                    </p>
                                </div>
                            </td>
                        </tr>
                    </table>
                </td>
            </tr>
        </table>
    </body>
    </html>
    """

    text_content = (
        f"{greeting_name}\n\n"
        f"You requested to reset your password for your GenZ Media account.\n"
        f"Visit the following link to reset your password:\n{reset_url}\n\n"
        f"This link expires in {settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES} minutes.\n"
        f"If you did not make this request, please ignore this email."
    )

    return await send_email(
        to_email=to_email,
        subject=subject,
        html_content=html_content,
        text_content=text_content,
    )
