import logging
import smtplib
import subprocess
from datetime import date
from email.mime.text import MIMEText

import requests

import config

log = logging.getLogger(__name__)


def _format_message(earliest: date) -> tuple[str, str]:
    subject = f"Arya Derm: earlier appointment available — {earliest.strftime('%B %d, %Y')}"
    body = (
        f"An earlier appointment slot opened up!\n\n"
        f"Earliest available date: {earliest.strftime('%A, %B %d, %Y')}\n\n"
        f"Book now: {config.ARYADERM_APPOINTMENTS_URL}\n"
    )
    return subject, body


def send_email(earliest: date) -> None:
    if not all([config.GMAIL_ADDRESS, config.GMAIL_APP_PASSWORD, config.NOTIFY_EMAIL_TO]):
        log.debug("Email not configured, skipping")
        return
    subject, body = _format_message(earliest)
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = config.GMAIL_ADDRESS
    msg["To"] = config.NOTIFY_EMAIL_TO
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(config.GMAIL_ADDRESS, config.GMAIL_APP_PASSWORD)
            smtp.send_message(msg)
        log.info("Email sent to %s", config.NOTIFY_EMAIL_TO)
    except Exception:
        log.exception("Failed to send email")


def send_macos_notification(earliest: date) -> None:
    subject, body = _format_message(earliest)
    script = (
        f'display notification "{body[:200]}" '
        f'with title "{subject}" '
        f'sound name "Glass"'
    )
    try:
        subprocess.run(["osascript", "-e", script], check=True, capture_output=True)
        log.info("macOS notification sent")
    except Exception:
        log.exception("Failed to send macOS notification")


def send_ntfy(earliest: date) -> None:
    if not config.NTFY_TOPIC:
        log.debug("ntfy not configured, skipping")
        return
    subject, body = _format_message(earliest)
    try:
        resp = requests.post(
            f"https://ntfy.sh/{config.NTFY_TOPIC}",
            data=body,
            headers={
                "Title": subject,
                "Priority": "high",
                "Tags": "calendar",
            },
            timeout=10,
        )
        resp.raise_for_status()
        log.info("ntfy push sent to topic %s", config.NTFY_TOPIC)
    except Exception:
        log.exception("Failed to send ntfy notification")


def notify_all(earliest: date) -> None:
    send_macos_notification(earliest)
    send_email(earliest)
    send_ntfy(earliest)
