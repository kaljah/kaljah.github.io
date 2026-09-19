import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import current_app

def is_smtp_configured() -> bool:
    """Check if outbound SMTP configuration is active."""
    return bool(os.environ.get("SMTP_HOST") and os.environ.get("SMTP_USER"))

def send_email(to_email: str, subject: str, text_body: str, html_body: str = None) -> bool:
    """
    Dispatches outbound email using configured SMTP provider.
    Gracefully falls back to structured application logging when SMTP
    credentials are not configured (e.g. development, testing, staging).
    """
    from_email = os.environ.get("EMAIL_FROM", "noreply@ghg-enterprise.com")
    smtp_host = os.environ.get("SMTP_HOST")
    smtp_port = int(os.environ.get("SMTP_PORT", 587))
    smtp_user = os.environ.get("SMTP_USER")
    smtp_pass = os.environ.get("SMTP_PASSWORD")
    use_tls = os.environ.get("SMTP_USE_TLS", "true").lower() in ("true", "1", "yes")

    if not is_smtp_configured():
        # Clean local logging fallback
        current_app.logger.info(
            f"[EmailService MOCK] Outbound email dispatched to: {to_email} | Subject: '{subject}'\n"
            f"  Content: {text_body[:200]}..."
        )
        return True

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = from_email
        msg["To"] = to_email

        msg.attach(MIMEText(text_body, "plain", "utf-8"))
        if html_body:
            msg.attach(MIMEText(html_body, "html", "utf-8"))

        with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as server:
            if use_tls:
                server.starttls()
            if smtp_user and smtp_pass:
                server.login(smtp_user, smtp_pass)
            server.send_message(msg)

        current_app.logger.info(f"[EmailService] Email successfully sent to {to_email} via {smtp_host}")
        return True
    except Exception as err:
        current_app.logger.error(f"[EmailService ERROR] Failed to send email to {to_email}: {err}")
        return False

def send_password_reset_email(to_email: str, user_name: str, reset_link: str = None) -> bool:
    """Send formatted password reset request email."""
    subject = "[GHG Enterprise] Password Reset Request"
    text_body = (
        f"Hello {user_name or 'User'},\n\n"
        f"A password reset was requested for your account ({to_email}).\n"
        f"If you requested this, an administrator will process your reset in User Management.\n\n"
        f"If you did not make this request, please contact your security officer immediately.\n\n"
        f"— GHG Enterprise Security Team"
    )
    html_body = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #e2e8f0; border-radius: 8px;">
        <h2 style="color: #0f172a; margin-bottom: 16px;">Password Reset Request</h2>
        <p>Hello <strong>{user_name or 'User'}</strong>,</p>
        <p>A password reset request was logged for your account (<code>{to_email}</code>).</p>
        <p>Your platform IT Administrator has been notified to verify your identity and authorize a reset token.</p>
        <div style="margin-top: 24px; padding: 12px; background: #f8fafc; border-left: 4px solid #ff6600; font-size: 0.85rem; color: #64748b;">
            If you did not request this, please notify your IT Security administrator immediately.
        </div>
        <p style="margin-top: 24px; font-size: 0.8rem; color: #94a3b8;">&copy; GHG Enterprise Carbon Accounting Platform</p>
    </div>
    """
    return send_email(to_email, subject, text_body, html_body)

def send_batch_review_alert(admin_email: str, batch_count: int, uploader_name: str) -> bool:
    """Send alert to administrators when new batch uploads require maker-checker approval."""
    subject = f"[Action Required] {batch_count} Emission Records Awaiting Review"
    text_body = (
        f"Hello Administrator,\n\n"
        f"A batch of {batch_count} new emission records was submitted by {uploader_name} and is currently pending maker-checker verification.\n\n"
        f"Please log into the GHG Platform to review and approve or reject these records.\n\n"
        f"— GHG Enterprise Platform"
    )
    html_body = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #e2e8f0; border-radius: 8px;">
        <h2 style="color: #0f172a; margin-bottom: 16px;">Emissions Pending Review</h2>
        <p>A new bulk upload batch of <strong>{batch_count} emission records</strong> was uploaded by <strong>{uploader_name}</strong>.</p>
        <p>Under enterprise Maker-Checker controls, these records require review and sign-off before inclusion in official ESG disclosures.</p>
        <p style="margin-top: 24px; font-size: 0.8rem; color: #94a3b8;">&copy; GHG Enterprise Carbon Accounting Platform</p>
    </div>
    """
    return send_email(admin_email, subject, text_body, html_body)
