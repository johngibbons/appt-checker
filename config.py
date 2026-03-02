import os
from dotenv import load_dotenv

load_dotenv()


def _get(key: str, default: str = "") -> str:
    return os.getenv(key, default).strip()


NEXHEALTH_BOOKING_URL = _get("NEXHEALTH_BOOKING_URL")
PROVIDER_NAMES = [n.strip() for n in _get("PROVIDER_NAMES", "Forum Patel,Lavanya Krishnan").split(",") if n.strip()]
APPOINTMENT_TYPE = _get("APPOINTMENT_TYPE", "Follow")

CHECK_INTERVAL_MINUTES = int(_get("CHECK_INTERVAL_MINUTES", "15"))
HEADLESS = _get("HEADLESS", "true").lower() == "true"

GMAIL_ADDRESS = _get("GMAIL_ADDRESS")
GMAIL_APP_PASSWORD = _get("GMAIL_APP_PASSWORD")
NOTIFY_EMAIL_TO = _get("NOTIFY_EMAIL_TO")

NTFY_TOPIC = _get("NTFY_TOPIC")

ARYADERM_APPOINTMENTS_URL = "https://www.aryaderm.com/appointments/"
DEBUG_DIR = os.path.join(os.path.dirname(__file__), "debug")
STATE_FILE = os.path.join(os.path.dirname(__file__), "state.json")
