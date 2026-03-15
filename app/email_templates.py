"""
Kindred v1.9.0 - HTML Email Templates
Templates for verification, password reset, match notifications.
"""

import html


def _base_template(content: str, title: str = "Kindred") -> str:
    return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title></head>
<body style="margin:0;padding:0;background:#1e1e2e;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#1e1e2e;padding:40px 20px;">
<tr><td align="center">
<table width="600" cellpadding="0" cellspacing="0" style="background:#313244;border-radius:12px;overflow:hidden;">
<tr><td style="background:linear-gradient(135deg,#cba6f7,#89b4fa);padding:30px;text-align:center;">
<h1 style="margin:0;color:#1e1e2e;font-size:28px;">Kindred</h1>
</td></tr>
<tr><td style="padding:30px;color:#cdd6f4;">
{content}
</td></tr>
<tr><td style="padding:20px 30px;text-align:center;color:#6c7086;font-size:12px;border-top:1px solid #45475a;">
You received this email because you have a Kindred account.<br>
If you didn't request this, you can safely ignore it.
</td></tr>
</table>
</td></tr></table>
</body></html>"""


def email_verification_template(display_name: str, verify_url: str) -> str:
    display_name = html.escape(display_name)
    verify_url = html.escape(verify_url)
    content = f"""
<h2 style="color:#cba6f7;margin:0 0 20px;">Verify Your Email</h2>
<p style="margin:0 0 15px;line-height:1.6;">Hi {display_name},</p>
<p style="margin:0 0 25px;line-height:1.6;">Welcome to Kindred! Please verify your email address to get started.</p>
<p style="text-align:center;margin:0 0 25px;">
<a href="{verify_url}" style="display:inline-block;background:#cba6f7;color:#1e1e2e;padding:14px 32px;border-radius:8px;text-decoration:none;font-weight:600;font-size:16px;">Verify Email</a>
</p>
<p style="margin:0;color:#6c7086;font-size:13px;">This link expires in 24 hours.</p>"""
    return _base_template(content, "Verify Your Email - Kindred")


def password_reset_template(display_name: str, reset_url: str) -> str:
    display_name = html.escape(display_name)
    reset_url = html.escape(reset_url)
    content = f"""
<h2 style="color:#cba6f7;margin:0 0 20px;">Reset Your Password</h2>
<p style="margin:0 0 15px;line-height:1.6;">Hi {display_name},</p>
<p style="margin:0 0 25px;line-height:1.6;">We received a request to reset your password. Click the button below to choose a new one.</p>
<p style="text-align:center;margin:0 0 25px;">
<a href="{reset_url}" style="display:inline-block;background:#cba6f7;color:#1e1e2e;padding:14px 32px;border-radius:8px;text-decoration:none;font-weight:600;font-size:16px;">Reset Password</a>
</p>
<p style="margin:0;color:#6c7086;font-size:13px;">This link expires in 1 hour. If you didn't request this, no action is needed.</p>"""
    return _base_template(content, "Reset Password - Kindred")


def new_match_template(display_name: str, match_name: str, match_score: float, app_url: str) -> str:
    display_name = html.escape(display_name)
    match_name = html.escape(match_name)
    app_url = html.escape(app_url)
    score_pct = round(match_score)
    content = f"""
<h2 style="color:#cba6f7;margin:0 0 20px;">New Match!</h2>
<p style="margin:0 0 15px;line-height:1.6;">Hi {display_name},</p>
<p style="margin:0 0 20px;line-height:1.6;">Great news - you matched with <strong style="color:#f5c2e7;">{match_name}</strong>!</p>
<div style="background:#1e1e2e;border-radius:8px;padding:20px;text-align:center;margin:0 0 25px;">
<div style="font-size:36px;font-weight:700;color:#a6e3a1;">{score_pct}%</div>
<div style="color:#6c7086;font-size:14px;">Compatibility Score</div>
</div>
<p style="text-align:center;margin:0 0 25px;">
<a href="{app_url}" style="display:inline-block;background:#cba6f7;color:#1e1e2e;padding:14px 32px;border-radius:8px;text-decoration:none;font-weight:600;font-size:16px;">View Match</a>
</p>"""
    return _base_template(content, "New Match - Kindred")


def match_expiring_template(display_name: str, match_name: str, days_left: int, app_url: str) -> str:
    display_name = html.escape(display_name)
    match_name = html.escape(match_name)
    app_url = html.escape(app_url)
    content = f"""
<h2 style="color:#fab387;margin:0 0 20px;">Match Expiring Soon</h2>
<p style="margin:0 0 15px;line-height:1.6;">Hi {display_name},</p>
<p style="margin:0 0 25px;line-height:1.6;">Your match with <strong style="color:#f5c2e7;">{match_name}</strong> expires in <strong style="color:#fab387;">{days_left} day{'s' if days_left != 1 else ''}</strong>. Send a message to keep the connection!</p>
<p style="text-align:center;margin:0 0 25px;">
<a href="{app_url}" style="display:inline-block;background:#fab387;color:#1e1e2e;padding:14px 32px;border-radius:8px;text-decoration:none;font-weight:600;font-size:16px;">Send Message</a>
</p>"""
    return _base_template(content, "Match Expiring - Kindred")


def safety_alert_template(display_name: str, emergency_contact: str) -> str:
    display_name = html.escape(display_name)
    emergency_contact = html.escape(emergency_contact)
    content = f"""
<h2 style="color:#f38ba8;margin:0 0 20px;">Safety Alert</h2>
<p style="margin:0 0 15px;line-height:1.6;">Hi,</p>
<p style="margin:0 0 25px;line-height:1.6;"><strong style="color:#f5c2e7;">{display_name}</strong> set up a safety check-in on Kindred and hasn't responded. They listed you ({emergency_contact}) as their emergency contact.</p>
<p style="margin:0 0 15px;line-height:1.6;color:#fab387;">Please check in with them to make sure they're safe.</p>"""
    return _base_template(content, "Safety Alert - Kindred")


def get_template_list() -> list[dict]:
    """Return list of available templates for admin preview."""
    return [
        {"id": "email_verification", "name": "Email Verification", "description": "Sent when user registers"},
        {"id": "password_reset", "name": "Password Reset", "description": "Sent on password reset request"},
        {"id": "new_match", "name": "New Match", "description": "Sent when users match"},
        {"id": "match_expiring", "name": "Match Expiring", "description": "Sent before match expires"},
        {"id": "safety_alert", "name": "Safety Alert", "description": "Sent to emergency contacts"},
    ]


def preview_template(template_id: str) -> str:
    """Return HTML preview of a template with sample data."""
    previews = {
        "email_verification": email_verification_template("Alex", "https://kindred.app/verify/sample-token"),
        "password_reset": password_reset_template("Alex", "https://kindred.app/reset/sample-token"),
        "new_match": new_match_template("Alex", "Jordan", 87.5, "https://kindred.app"),
        "match_expiring": match_expiring_template("Alex", "Jordan", 2, "https://kindred.app"),
        "safety_alert": safety_alert_template("Alex", "friend@example.com"),
    }
    return previews.get(template_id, "<p>Template not found</p>")
