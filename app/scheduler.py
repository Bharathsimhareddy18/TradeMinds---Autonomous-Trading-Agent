from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from datetime import datetime, timedelta
import pytz
import asyncio
from app.logger import get_logger

logger = get_logger(__name__)

IST = pytz.timezone("Asia/Kolkata")

MARKET_OPEN_HOUR = 9
MARKET_OPEN_MINUTE = 20
MARKET_CLOSE_HOUR = 15
MARKET_CLOSE_MINUTE = 25

scheduler = AsyncIOScheduler(timezone=IST)
JOB_LOCK = asyncio.Lock()


def is_market_open() -> bool:
    """Check if NSE market is currently open."""
    now = datetime.now(IST)
    if now.weekday() >= 5:
        return False
    market_open = now.replace(hour=MARKET_OPEN_HOUR, minute=MARKET_OPEN_MINUTE, second=0, microsecond=0)
    market_close = now.replace(hour=MARKET_CLOSE_HOUR, minute=MARKET_CLOSE_MINUTE, second=0, microsecond=0)
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

    MIN_MINUTES = 5
    MAX_MINUTES = 1440
    try:
        suggested_minutes = float(next_trigger)
    except Exception:
        suggested_minutes = 60.0

    clamped_minutes = int(max(MIN_MINUTES, min(suggested_minutes, MAX_MINUTES)))

    now = datetime.now(IST)
    next_run = now + timedelta(minutes=clamped_minutes)
    market_close = now.replace(hour=MARKET_CLOSE_HOUR, minute=MARKET_CLOSE_MINUTE, second=0, microsecond=0)

    if next_run >= market_close:
        next_day = now
        while True:
            next_day = next_day + timedelta(days=1)
            if next_day.weekday() < 5:
                break
        next_open = next_day.replace(hour=MARKET_OPEN_HOUR, minute=MARKET_OPEN_MINUTE, second=0, microsecond=0)
        scheduler.add_job(
            scalp_job,
            trigger=DateTrigger(run_date=next_open, timezone=IST),
            id="scalp_dynamic",
            replace_existing=True,
        )
        logger.info(
            f"[Scheduler] Past market close. Next scalp at {next_open.strftime('%Y-%m-%d %H:%M')}"
        )
        return

    scheduler.add_job(
        scalp_job,
        trigger=DateTrigger(run_date=next_run, timezone=IST),
        id="scalp_dynamic",
        replace_existing=True,
    )
    logger.info(f"[Scheduler] Next scalp check at {next_run.strftime('%Y-%m-%d %H:%M IST')} ({clamped_minutes} mins)")


async def momentum_buy_job():
    """Runs at 9:20 AM — momentum buy."""
    from app.services.momentum_agent import run_momentum_buy
    async with JOB_LOCK:
        if not is_market_open():
            return
        logger.info("[Scheduler] Momentum BUY agent running.")
        await run_momentum_buy()


async def momentum_sell_job():
    """Runs at 3:15 PM — close positions + day summary."""
    from app.services.momentum_agent import run_momentum_sell
    async with JOB_LOCK:
        logger.info("[Scheduler] Momentum SELL agent running.")
        await run_momentum_sell()


def start_scheduler():
    scheduler.add_job(
        momentum_buy_job,
        CronTrigger(hour=MARKET_OPEN_HOUR, minute=MARKET_OPEN_MINUTE, day_of_week="mon-fri", timezone=IST),
        id="momentum_buy",
    )
    scheduler.add_job(
        momentum_sell_job,
        CronTrigger(hour=15, minute=15, day_of_week="mon-fri", timezone=IST),
        id="momentum_sell",
    )
    scheduler.add_job(
        scalp_job,
        CronTrigger(hour=10, minute=55, day_of_week="mon-fri", timezone=IST),
        id="scalp_initial",
    )
    scheduler.start()
    logger.info("[Scheduler] Started. Waiting for market hours.")