from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from datetime import datetime, timedelta
import pytz
from app.logger import get_logger

logger = get_logger(__name__)

IST = pytz.timezone("Asia/Kolkata")
scheduler = AsyncIOScheduler(timezone=IST)


def is_market_open() -> bool:
    """Check if NSE market is currently open."""
    now = datetime.now(IST)
    if now.weekday() >= 5:  # Saturday=5, Sunday=6
        return False
    market_open = now.replace(hour=9, minute=15, second=0, microsecond=0)
    market_close = now.replace(hour=15, minute=30, second=0, microsecond=0)
    return market_open <= now <= market_close


async def scalp_job():
    """Runs scalp agent. LLM decides next trigger time."""
    from app.services.scalp_agent import run_scalp_agent

    if not is_market_open():
        logger.info("[Scheduler] Market closed. Skipping scalp job.")
        return
    logger.info(f"[Scheduler] Scalp agent waking up at {datetime.now(IST).strftime('%H:%M IST')}")

    result = await run_scalp_agent()
    next_trigger = result.get("next_trigger_minutes", 60)

    # Clamp LLM-suggested next trigger (in minutes) between 300s and 86400s.
    # That corresponds to 5 minutes and 1440 minutes respectively.
    MIN_MINUTES = 300 / 60
    MAX_MINUTES = 86400 / 60
    try:
        suggested_minutes = float(next_trigger)
    except Exception:
        suggested_minutes = 60.0

    clamped_minutes = max(MIN_MINUTES, min(suggested_minutes, MAX_MINUTES))

    # Calculate next run time using clamped minutes
    next_run = datetime.now(IST) + timedelta(minutes=clamped_minutes)
    market_close = datetime.now(IST).replace(hour=15, minute=30, second=0, microsecond=0)

    if next_run >= market_close:
        logger.info(f"[Scheduler] Next run {next_run.strftime('%H:%M')} is past market close. Stopping for today.")
        return

    # Schedule one-time next run
    scheduler.add_job(
        scalp_job,
        trigger=DateTrigger(run_date=next_run, timezone=IST),
        id="scalp_dynamic",
        replace_existing=True,
    )
    logger.info(f"[Scheduler] Next scalp check at {next_run.strftime('%H:%M IST')} ({int(clamped_minutes)} mins)")


async def momentum_buy_job():
    """Runs at 9:15 AM — momentum buy."""
    from app.services.momentum_agent import run_momentum_buy

    if not is_market_open():
        return

    logger.info("[Scheduler] Momentum BUY agent running.")
    await run_momentum_buy()


async def momentum_sell_job():
    """Runs at 3:15 PM — close positions + day summary."""
    from app.services.momentum_agent import run_momentum_sell

    logger.info("[Scheduler] Momentum SELL agent running.")
    await run_momentum_sell()


def start_scheduler():
    # Momentum buy — 9:15 AM every weekday
    scheduler.add_job(
        momentum_buy_job,
        CronTrigger(hour=9, minute=15, day_of_week="mon-fri", timezone=IST),
        id="momentum_buy",
    )

    # Momentum sell — 3:15 PM every weekday
    scheduler.add_job(
        momentum_sell_job,
        CronTrigger(hour=15, minute=15, day_of_week="mon-fri", timezone=IST),
        id="momentum_sell",
    )

    # First scalp job — 9:15 AM every weekday (LLM takes over after this)
    scheduler.add_job(
        scalp_job,
        CronTrigger(hour=9, minute=15, day_of_week="mon-fri", timezone=IST),
        id="scalp_initial",
    )

    scheduler.start()
    logger.info("[Scheduler] Started. Waiting for market hours.")