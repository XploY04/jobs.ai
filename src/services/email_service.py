"""Email service using Gmail SMTP (matches remotestar-backend pattern)."""

from __future__ import annotations

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from src.utils.config import settings
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


def send_email(to: str, subject: str, html_body: str) -> bool:
    """Send an email via Gmail SMTP. Returns True on success."""
    if not settings.email_user or not settings.email_password:
        logger.warning("Email credentials not configured, skipping email to %s", to)
        return False

    msg = MIMEMultipart("alternative")
    msg["From"] = settings.email_user
    msg["To"] = to
    msg["Subject"] = subject
    msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(settings.email_user, settings.email_password)
            server.sendmail(settings.email_user, to, msg.as_string())
        logger.info("Email sent to %s: %s", to, subject)
        return True
    except Exception as e:
        logger.error("Failed to send email to %s: %s", to, e)
        return False


def send_matching_paused_email(
    to: str,
    first_name: str,
    credit_balance: int,
    match_count: int = 0,
) -> bool:
    """Send email when weekly matching is paused due to insufficient credits."""

    candidate_url = settings.candidate_app_url or "https://candidate.remotestar.io"
    credits_url = f"{candidate_url}/credits"

    match_line = ""
    if match_count > 0:
        match_line = f"""
        <div style="background:#e8f4f8;border-radius:8px;padding:16px 20px;margin:20px 0;text-align:center;">
          <p style="font-size:2rem;font-weight:bold;color:#246a81;margin:0 0 4px 0;">{match_count}</p>
          <p style="font-size:0.9rem;color:#45556c;margin:0;">jobs matched your profile last time</p>
        </div>
        """

    html = f"""
    <div style="background:#f4f4f7;padding:30px 0;min-height:100vh;font-family:Arial,'Poppins',sans-serif;">
      <div style="max-width:480px;margin:40px auto;background:#fff;border-radius:10px;box-shadow:0 2px 8px rgba(0,0,0,0.08);overflow:hidden;">

        <div style="background:linear-gradient(to bottom,#246a81,#1a5d73);padding:32px 0;text-align:center;">
          <img src="https://cdn.prod.website-files.com/6109129e0eb56858fd233306/6109129e0eb56827f323332c_LOGO-p-500.png"
               alt="RemoteStar" style="height:40px;width:auto;filter:brightness(0) invert(1);" />
        </div>

        <div style="padding:32px 28px 24px 28px;">
          <p style="font-size:1.1rem;margin-bottom:20px;color:#0c2d3b;">
            Hi <b>{first_name}</b>,
          </p>

          <p style="font-size:1rem;margin-bottom:16px;color:#45556c;line-height:1.6;">
            Your <b>weekly job matching</b> has been paused because your credit balance
            (<b>{credit_balance} credits</b>) is below the <b>50 credits</b> needed for a match run.
          </p>

          {match_line}

          <p style="font-size:1rem;margin-bottom:24px;color:#45556c;line-height:1.6;">
            Add credits to keep getting personalized job recommendations matched to your
            skills and experience every week.
          </p>

          <div style="text-align:center;margin:28px 0;">
            <a href="{credits_url}"
               style="display:inline-block;padding:14px 32px;background:linear-gradient(to bottom,#2a8ca3,#1a5d73);color:#ffffff;text-decoration:none;border-radius:8px;font-weight:bold;font-size:1rem;">
              Add Credits
            </a>
          </div>

          <p style="font-size:0.85rem;color:#94a3b8;text-align:center;margin-top:20px;">
            50 credits = 1 weekly match run ($0.25)
          </p>

          <p style="margin-top:32px;font-size:0.95rem;color:#94a3b8;">
            Best regards,<br>RemoteStar Team
          </p>
        </div>

        <div style="background:#f4f4f7;padding:16px;text-align:center;font-size:0.85rem;color:#aaa;">
          &copy; 2026 RemoteStar. All rights reserved.
        </div>
      </div>
    </div>
    """

    return send_email(to, "Your weekly job matching is paused", html)
