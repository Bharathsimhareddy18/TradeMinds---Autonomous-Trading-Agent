import asyncio
from datetime import datetime, timezone
from app.config import supabase
from app.utils.get_current_stock_price import get_stock_current_price
from app.utils.calculate_pnl import calculate_pnl
from tenacity import stop_after_attempt, wait_fixed, retry 



@retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
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
    Execute a paper trade — buy, wait, sell, log to DB.

    Args:
        symbol (str): NSE symbol e.g. RELIANCE.NS
        amount (float): Amount in INR to invest
        hold_seconds (int): How long to hold before selling
        kind (str): MOMENTUM or SCALP
        reasoning (str): Why LLM decided to trade
        news_at_moment (str): News headlines that triggered this trade
        next_trigger_minutes (int): When LLM wants to be woken up next

    Returns:
        dict: Full trade result
    """

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

    # 4. Wait for hold period
    await asyncio.sleep(hold_seconds)

    # 5. Fetch exit price
    exit_data = await get_stock_current_price(symbol)
    exit_price = exit_data.get("current_price", entry_price)

    # 6. Calculate P&L
    pnl_result = calculate_pnl(entry_price, exit_price, amount)
    pnl = pnl_result["pnl"]
    new_balance = round(balance - amount + amount + pnl, 2)  # amount returned + pnl

    # 7. Update account
    supabase.table("account").update({
        "balance": new_balance,
        "total_trades": account["total_trades"] + 1,
        "total_pnl": round(float(account["total_pnl"]) + pnl, 2),
        "wins": account["wins"] + (1 if pnl > 0 else 0),
        "losses": account["losses"] + (1 if pnl < 0 else 0),
        "last_updated": datetime.now(timezone.utc).isoformat(),
    }).eq("id", 1).execute()

    # 8. Log trade to DB
    supabase.table("trades").insert({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "kind": kind,
        "symbol": symbol,
        "action": "BUY_SELL",
        "amount_spent": amount,
        "trade_window_seconds": hold_seconds,
        "entry_price": entry_price,
        "exit_price": exit_price,
        "pnl": pnl,
        "balance_after": new_balance,
        "news_at_moment": news_at_moment[:2000],
        "reasoning": reasoning,
        "next_trigger_minutes": next_trigger_minutes,
    }).execute()

    return {
        "symbol": symbol,
        "amount": amount,
        "entry_price": entry_price,
        "exit_price": exit_price,
        "units": pnl_result["units"],
        "pnl": pnl,
        "pnl_pct": pnl_result["pnl_pct"],
        "result": pnl_result["result"],
        "balance_after": new_balance,
        "hold_seconds": hold_seconds,
    }