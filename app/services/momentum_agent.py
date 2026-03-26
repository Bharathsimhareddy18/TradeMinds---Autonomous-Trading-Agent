from openai import OpenAI
from app.config import supabase
from app.utils.get_top_movers import get_top_movers
from app.utils.get_stock_trends_data import get_stock_trends_data
from app.utils.get_current_stock_price import get_stock_current_price
from app.utils.get_account_balance import get_account_balance
from app.utils.get_news import get_news
from app.prompts import MOMENTUM_BUY_PROMPT
from datetime import datetime, timezone
import json
from pydantic import BaseModel, ValidationError
from app.logger import get_logger

logger = get_logger(__name__)

class Trade(BaseModel):
    symbol: str
    amount: float
    reasoning: str

class TradeDecision(BaseModel):
    trades: list[Trade]
    skip: bool
    skip_reason: str = ""
client = OpenAI()


async def run_momentum_buy():
    """
    Morning run — LLM scans top movers, checks trends,
    picks strongest momentum stocks and opens BUY positions.
    """
    
    logger.info("Starting morning run...")

    # Gather context for LLM
    movers = await get_top_movers()
    news = get_news()
    balance = get_account_balance()

    # Check trends for each top mover
    trends = []
    for mover in movers:
        trend = await get_stock_trends_data(mover["symbol"])
        trends.append(trend)

    # Build user message
    user_message = f"""
Market is open. Here is the current data:

Account Balance: {json.dumps(balance)}

Top 10 Movers Today: {json.dumps(movers)}

Trend Analysis: {json.dumps(trends)}

Latest News: {json.dumps(news)}

Analyze this data and decide which stocks to buy for momentum trading.
Only buy stocks with BULLISH trend and 2+ consecutive up days.
Return your decision as JSON in this exact format:

{{
    "trades": [
        {{
            "symbol": "RELIANCE.NS",
            "amount": 15000,
            "reasoning": "why you picked this stock"
        }}
    ],
    "skip": false,
    "skip_reason": ""
}}

If no strong signal found, set skip to true and explain why.
Max 2 trades. Max ₹40,000 per trade.
"""
    logger.info("Sending data to LLM for analysis...")
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": MOMENTUM_BUY_PROMPT},
            {"role": "user", "content": user_message},
        ],
        response_format={"type": "json_object"},
    )

    try:
        raw = json.loads(response.choices[0].message.content)
        decision = TradeDecision(**raw)
    except (json.JSONDecodeError, ValidationError) as e:
        logger.error(f"LLM response validation failed: {e}")
        return

    if decision.get("skip"):
        logger.info(f"Skipping. Reason: {decision.get('skip_reason')}",name=__name__)
        # Log skip to DB
        supabase.table("trades").insert({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "kind": "MOMENTUM",
            "action": "SKIP",
            "reasoning": decision.get("skip_reason"),
            "balance_after": balance["balance"],
            "status": "CLOSED",
        }).execute()
        return

    # Execute each trade — open position in DB
    for trade in decision.get("trades", []):
        symbol = trade["symbol"]
        amount = trade["amount"]
        reasoning = trade["reasoning"]

        # Fetch entry price
        price_data = await get_stock_current_price(symbol)
        if "error" in price_data:
            print(f"[Momentum] Could not fetch price for {symbol}")
            continue

        entry_price = price_data["current_price"]
        current_balance = get_account_balance()["balance"]

        if current_balance < amount:
            print(f"[Momentum] Insufficient balance for {symbol}")
            continue

        # Deduct from balance
        supabase.table("account").update({
            "balance": round(current_balance - amount, 2),
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }).eq("id", 1).execute()

        # Log open position
        supabase.table("trades").insert({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "kind": "MOMENTUM",
            "symbol": symbol,
            "action": "BUY",
            "amount_spent": amount,
            "entry_price": entry_price,
            "balance_after": round(current_balance - amount, 2),
            "reasoning": reasoning,
            "news_at_moment": json.dumps([n["title"] for n in news[:5]]),
            "status": "OPEN",
        }).execute()

        logger.info(f"Bought {symbol} at ₹{entry_price} — Amount: ₹{amount}")


async def run_momentum_sell():
    """
    Afternoon run — fetch all open momentum positions,
    get current prices, calculate P&L, close positions.
    """

    # Fetch all open momentum positions
    open_trades = supabase.table("trades") \
        .select("*") \
        .eq("kind", "MOMENTUM") \
        .eq("status", "OPEN") \
        .execute().data

    if not open_trades:
        logger.info("[Momentum] No open positions to close.")
        return

    total_pnl = 0

    for trade in open_trades:
        symbol = trade["symbol"]
        entry_price = float(trade["entry_price"])
        amount = float(trade["amount_spent"])

        # Fetch exit price
        price_data = await get_stock_current_price(symbol)
        exit_price = price_data.get("current_price", entry_price)

        # Calculate P&L
        units = amount / entry_price
        pnl = round((exit_price - entry_price) * units, 2)
        total_pnl += pnl

        # Get current balance
        account = supabase.table("account").select("*").eq("id", 1).execute().data[0]
        current_balance = float(account["balance"])
        new_balance = round(current_balance + amount + pnl, 2)

        # Update account
        supabase.table("account").update({
            "balance": new_balance,
            "total_trades": account["total_trades"] + 1,
            "total_pnl": round(float(account["total_pnl"]) + pnl, 2),
            "wins": account["wins"] + (1 if pnl > 0 else 0),
            "losses": account["losses"] + (1 if pnl < 0 else 0),
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }).eq("id", 1).execute()

        # Close the trade
        supabase.table("trades").update({
            "exit_price": exit_price,
            "pnl": pnl,
            "balance_after": new_balance,
            "status": "CLOSED",
        }).eq("id", trade["id"]).execute()

        logger.info(f"[Momentum] Closed {symbol} | Entry: ₹{entry_price} | Exit: ₹{exit_price} | P&L: ₹{pnl}")

    logger.info(f"[Momentum] Day closed. Total P&L: ₹{round(total_pnl, 2)}")
