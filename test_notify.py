"""Send a test notification through all configured channels."""

import sys
from datetime import date

import config
import notify

def main():
    test_date = date(2026, 3, 15)  # fake date for testing

    print("=== Notification Test ===")
    print(f"Test date: {test_date.strftime('%A, %B %d, %Y')}")
    print()

    # Check what's configured
    has_email = all([config.GMAIL_ADDRESS, config.GMAIL_APP_PASSWORD, config.NOTIFY_EMAIL_TO])
    has_ntfy = bool(config.NTFY_TOPIC)

    print(f"Email configured:  {'YES' if has_email else 'NO (GMAIL_ADDRESS, GMAIL_APP_PASSWORD, NOTIFY_EMAIL_TO)'}")
    print(f"ntfy configured:   {'YES' if has_ntfy else 'NO (NTFY_TOPIC)'}")
    print(f"macOS notification: always available")
    print()

    if not has_email and not has_ntfy:
        print("WARNING: No remote notification channels configured!")
        print("You'll only get macOS desktop notifications (local only).")
        print()
        print("Quick setup for phone notifications:")
        print("  1. Install ntfy app on your phone (ntfy.sh)")
        print("  2. Subscribe to a unique topic name")
        print("  3. Set NTFY_TOPIC in .env to that topic name")
        print("  4. Re-run this script")
        print()

    channel = sys.argv[1] if len(sys.argv) > 1 else "all"

    if channel == "all":
        print("Sending test via ALL channels...")
        notify.notify_all(test_date)
    elif channel == "email":
        print("Sending test email...")
        notify.send_email(test_date)
    elif channel == "ntfy":
        print("Sending test ntfy push...")
        notify.send_ntfy(test_date)
    elif channel == "macos":
        print("Sending test macOS notification...")
        notify.send_macos_notification(test_date)
    else:
        print(f"Unknown channel: {channel}")
        print("Usage: python test_notify.py [all|email|ntfy|macos]")
        sys.exit(1)

    print("Done!")


if __name__ == "__main__":
    main()
