import asyncio
from datetime import datetime, timezone
from app.config import supabase
from app.utils.get_current_stock_price import get_stock_current_price
from app.utils.calculate_pnl import calculate_pnl
from app.logger import get_logger

logger = get_logger(__name__)

STOP_LOSS_PCT = 0.5      # sell if price drops more than 0.5% below entry
CHECK_INTERVAL = 60      # check price every 60 seconds
MAX_HOLD_SECONDS = 600   # exit no matter what after 600 seconds


async def buy_stock(
    symbol: str,
    amount: float,
    hold_seconds: int,
    kind: str,
    reasoning: str,
    news_at_moment: str,
    next_trigger_minutes: int,
) -> dict:
    """
    Execute a paper trade with smart exit logic:
    - Sell immediately if price goes above entry (profit)
    - Sell immediately if price drops more than 0.5% (stop loss)
    - Wait if price is slightly below entry (within 0.5%)
    - Force sell after MAX_HOLD_SECONDS no matter what
    """

    if not hasattr(buy_stock, "_lock"):
        buy_stock._lock = asyncio.Lock()

    async with buy_stock._lock:
        # 1. Check balance
        account = supabase.table("account").select("*").eq("id", 1).execute().data[0]
        balance = float(account["balance"])

        if balance < amount:
            return {"error": f"Insufficient balance. Available: ₹{balance}, Requested: ₹{amount}"}

        # 2. Fetch entry price
        entry_data = await get_stock_current_price(symbol)
        if "error" in entry_data:
            return {"error": f"Could not fetch entry price: {entry_data['error']}"}
        entry_price = entry_data["current_price"]

        # 3. Deduct amount from balance immediately
        supabase.table("account").update({
            "balance": round(balance - amount, 2),
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }).eq("id", 1).execute()

    # 4. Smart exit loop
    elapsed = 0
    exit_price = entry_price
    exit_reason = "time_expired"
    stop_loss_threshold = entry_price * (1 - STOP_LOSS_PCT / 100)

    logger.info(
        f"[Trade] {symbol} | Entry: ₹{entry_price} | "
        f"Stop loss: ₹{round(stop_loss_threshold, 2)} | "
        f"Max hold: {MAX_HOLD_SECONDS}s"
    )

    while elapsed < MAX_HOLD_SECONDS:
        await asyncio.sleep(CHECK_INTERVAL)
        elapsed += CHECK_INTERVAL

        current_data = await get_stock_current_price(symbol)
        if "error" in current_data:
            logger.warning(f"[Trade] Could not fetch price at {elapsed}s, continuing...")
            continue

        current_price = current_data["current_price"]
        change_pct = ((current_price - entry_price) / entry_price) * 100

        logger.info(
            f"[Trade] {symbol} | Elapsed: {elapsed}s | "
            f"Current: ₹{current_price} | Change: {round(change_pct, 2)}%"
        )

        if current_price > entry_price:
            exit_price = current_price
            exit_reason = "profit"
            logger.info(f"[Trade] {symbol} | PROFIT EXIT at ₹{exit_price} (+{round(change_pct, 2)}%)")
            break

        elif current_price < stop_loss_threshold:
            exit_price = current_price
            exit_reason = "stop_loss"
            logger.info(f"[Trade] {symbol} | STOP LOSS at ₹{exit_price} ({round(change_pct, 2)}%)")
            break

        else:
            logger.info(
                f"[Trade] {symbol} | Small dip ({round(change_pct, 2)}%), within 0.5% — waiting..."
            )

    else:
        # Max hold time reached — fetch final price and exit
        final_data = await get_stock_current_price(symbol)
        exit_price = final_data.get("current_price", entry_price)
        exit_reason = "time_expired"
        logger.info(f"[Trade] {symbol} | TIME EXPIRED | Exit at ₹{exit_price}")

    # 5. Calculate P&L
    pnl_result = calculate_pnl(entry_price, exit_price, amount)
    pnl = pnl_result["pnl"]
    new_balance = round(balance + pnl, 2)

    # 6. Update account
    supabase.table("account").update({
        "balance": new_balance,
        "total_trades": account["total_trades"] + 1,
        "total_pnl": round(float(account["total_pnl"]) + pnl, 2),
        "wins": account["wins"] + (1 if pnl > 0 else 0),
        "losses": account["losses"] + (1 if pnl < 0 else 0),
        "last_updated": datetime.now(timezone.utc).isoformat(),
    }).eq("id", 1).execute()

    # 7. Log trade to DB
    supabase.table("trades").insert({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "kind": kind,
        "symbol": symbol,
        "action": "BUY_SELL",
        "amount_spent": amount,
        "trade_window_seconds": elapsed,
        "entry_price": entry_price,
        "exit_price": exit_price,
        "pnl": pnl,
        "balance_after": new_balance,
        "news_at_moment": news_at_moment[:2000],
        "reasoning": reasoning,
        "next_trigger_minutes": next_trigger_minutes,
        "status": "CLOSED",
    }).execute()

    logger.info(
        f"[Trade] {symbol} CLOSED | Reason: {exit_reason} | "
        f"P&L: ₹{pnl} | Balance: ₹{new_balance}"
    )

    return {
        "symbol": symbol,
        "amount": amount,
        "entry_price": entry_price,
        "exit_price": exit_price,
        "units": pnl_result["units"],
        "pnl": pnl,
        "pnl_pct": pnl_result["pnl_pct"],
        "result": pnl_result["result"],
        "exit_reason": exit_reason,
        "elapsed_seconds": elapsed,
        "balance_after": new_balance,
    }