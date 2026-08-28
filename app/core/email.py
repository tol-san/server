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
    <html lang="en">
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{subject}</title>
    </head>
    <body style="margin: 0; padding: 0; background-color: #f9fafb; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #111827; -webkit-font-smoothing: antialiased;">
        <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background-color: #f9fafb; padding: 48px 16px;">
            <tr>
                <td align="center">
                    <table role="presentation" width="100%" style="max-width: 460px; background-color: #ffffff; border-radius: 12px; padding: 40px 36px; border: 1px solid #e5e7eb; box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);">
                        <!-- Brand Wordmark -->
                        <tr>
                            <td style="padding-bottom: 28px;">
                                <span style="font-size: 20px; font-weight: 800; letter-spacing: -0.5px; color: #061A33;">
                                    Gen<span style="color: #F20518;">Z</span> Media
                                </span>
                            </td>
                        </tr>
                        <!-- Heading -->
                        <tr>
                            <td style="padding-bottom: 16px;">
                                <h1 style="margin: 0; font-size: 20px; font-weight: 700; color: #111827; letter-spacing: -0.3px;">
                                    Reset your password
                                </h1>
                            </td>
                        </tr>
                        <!-- Body -->
                        <tr>
                            <td style="padding-bottom: 28px;">
                                <p style="margin: 0 0 14px; font-size: 15px; line-height: 24px; color: #374151;">
                                    {greeting_name}
                                </p>
                                <p style="margin: 0; font-size: 15px; line-height: 24px; color: #374151;">
                                    We received a request to reset your password. Click the button below to choose a new one:
                                </p>
                            </td>
                        </tr>
                        <!-- CTA Button -->
                        <tr>
                            <td style="padding-bottom: 20px;">
                                <a href="{reset_url}" style="background-color: #F20518; color: #ffffff; font-size: 14px; font-weight: 600; text-decoration: none; padding: 12px 28px; border-radius: 8px; display: inline-block; text-align: center;">
                                    Reset password
                                </a>
                            </td>
                        </tr>
                        <!-- In-App Token Support -->
                        <tr>
                            <td style="padding-bottom: 28px;">
                                <p style="margin: 0 0 6px; font-size: 13px; color: #6b7280;">
                                    Or paste this reset token directly in the app:
                                </p>
                                <div style="background-color: #f3f4f6; border-radius: 6px; padding: 10px 12px; font-family: monospace; font-size: 12px; color: #1f2937; word-break: break-all; border: 1px solid #e5e7eb;">
                                    {reset_token}
                                </div>
                            </td>
                        </tr>
                        <!-- Expiration & Disclaimer -->
                        <tr>
                            <td style="border-top: 1px solid #f3f4f6; padding-top: 24px;">
                                <p style="margin: 0 0 8px; font-size: 13px; line-height: 20px; color: #6b7280;">
                                    This link and token will expire in {settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES} minutes.
                                </p>
                                <p style="margin: 0; font-size: 13px; line-height: 20px; color: #9ca3af;">
                                    If you didn't request a password reset, you can safely ignore this email.
                                </p>
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
        f"Your reset token is: {reset_token}\n\n"
        f"This link expires in {settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES} minutes.\n"
        f"If you did not make this request, please ignore this email."
    )

    return await send_email(
        to_email=to_email,
        subject=subject,
        html_content=html_content,
        text_content=text_content,
    )


async def send_password_reset_otp_email(
    to_email: str,
    otp: str,
    username: Optional[str] = None,
) -> bool:
    """
    Compose and send a 6-digit verification code email for password reset.
    """
    greeting_name = f"Hi {username}," if username else "Hello,"
    subject = f"{otp} is your GenZ Media verification code"

    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{subject}</title>
    </head>
    <body style="margin: 0; padding: 0; background-color: #f9fafb; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #111827; -webkit-font-smoothing: antialiased;">
        <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background-color: #f9fafb; padding: 48px 16px;">
            <tr>
                <td align="center">
                    <table role="presentation" width="100%" style="max-width: 460px; background-color: #ffffff; border-radius: 12px; padding: 40px 36px; border: 1px solid #e5e7eb; box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);">
                        <!-- Brand Wordmark -->
                        <tr>
                            <td style="padding-bottom: 28px;">
                                <span style="font-size: 20px; font-weight: 800; letter-spacing: -0.5px; color: #061A33;">
                                    Gen<span style="color: #F20518;">Z</span> Media
                                </span>
                            </td>
                        </tr>
                        <!-- Heading -->
                        <tr>
                            <td style="padding-bottom: 16px;">
                                <h1 style="margin: 0; font-size: 20px; font-weight: 700; color: #111827; letter-spacing: -0.3px;">
                                    Verification Code
                                </h1>
                            </td>
                        </tr>
                        <!-- Body -->
                        <tr>
                            <td style="padding-bottom: 24px;">
                                <p style="margin: 0 0 14px; font-size: 15px; line-height: 24px; color: #374151;">
                                    {greeting_name}
                                </p>
                                <p style="margin: 0; font-size: 15px; line-height: 24px; color: #374151;">
                                    Enter the following 6-digit code in the GenZ Media app to reset your password:
                                </p>
                            </td>
                        </tr>
                        <!-- OTP Code Card -->
                        <tr>
                            <td style="padding-bottom: 28px;">
                                <div style="background-color: #f8fafc; border-radius: 10px; padding: 18px 24px; text-align: center; border: 1px solid #e2e8f0;">
                                    <span style="font-size: 32px; font-weight: 800; letter-spacing: 8px; color: #061A33; font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', Roboto, monospace;">
                                        {otp}
                                    </span>
                                </div>
                            </td>
                        </tr>
                        <!-- Expiration & Disclaimer -->
                        <tr>
                            <td style="border-top: 1px solid #f3f4f6; padding-top: 24px;">
                                <p style="margin: 0 0 8px; font-size: 13px; line-height: 20px; color: #6b7280;">
                                    This code will expire in {settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES} minutes.
                                </p>
                                <p style="margin: 0; font-size: 13px; line-height: 20px; color: #9ca3af;">
                                    If you didn't request a password reset, you can safely ignore this email. Never share this code with anyone.
                                </p>
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
        f"Your GenZ Media password reset code is: {otp}\n\n"
        f"Enter this 6-digit code in the app to set your new password.\n"
        f"This code will expire in {settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES} minutes.\n"
        f"If you didn't request this code, you can safely ignore this email."
    )

    return await send_email(
        to_email=to_email,
        subject=subject,
        html_content=html_content,
        text_content=text_content,
    )

