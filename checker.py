import asyncio
import logging
import sys
from logging.handlers import RotatingFileHandler

import config
import notify
import state
from browser import check_availability

log = logging.getLogger()


def setup_logging() -> None:
    log.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    # Rotating file handler
    fh = RotatingFileHandler("checker.log", maxBytes=5 * 1024 * 1024, backupCount=3)
    fh.setFormatter(fmt)
    log.addHandler(fh)

    # Stdout handler
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    log.addHandler(sh)


async def run_once() -> None:
    log.info("Starting availability check...")
    earliest = await check_availability()

    if earliest is None:
        log.warning("Could not determine earliest date this run")
        return

    log.info("Earliest available date: %s", earliest.isoformat())

    previous = state.load_earliest_date()
    if previous is None:
        log.info("First run — saving baseline date: %s", earliest.isoformat())
        state.save_earliest_date(earliest)
        return

    if earliest < previous:
        log.info("Earlier date found! %s < %s (previous). Sending notifications.", earliest, previous)
        state.save_earliest_date(earliest)
        notify.notify_all(earliest)
    else:
        log.info("No improvement. Earliest: %s, Previous best: %s", earliest, previous)
        # Update state if the date moved later (slot was taken)
        if earliest != previous:
            state.save_earliest_date(earliest)


async def main() -> None:
    setup_logging()
    once = "--once" in sys.argv
    log.info("Appointment checker started. Mode: %s. Headless: %s",
             "single run" if once else f"loop ({config.CHECK_INTERVAL_MINUTES}min)",
             config.HEADLESS)
    log.info("Providers: %s", ", ".join(config.PROVIDER_NAMES))

    if once:
        await run_once()
        return

    while True:
        try:
            await run_once()
        except Exception:
            log.exception("Unhandled error in run_once")

        log.info("Sleeping %d minutes...", config.CHECK_INTERVAL_MINUTES)
        await asyncio.sleep(config.CHECK_INTERVAL_MINUTES * 60)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("Shutting down.")
