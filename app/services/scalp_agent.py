# app/services/scalp_agent.py

import json
import asyncio
import functools
from app.config import openai_client, supabase, settings
from app.prompts import SCALP_PROMPT
from app.services.tools import TOOLS
from app.utils.get_news import get_news
from app.utils.get_top_movers import get_top_movers
from app.utils.get_current_stock_price import get_stock_current_price
from app.utils.get_stock_historical_data import get_stock_historical_data
from app.utils.get_stock_trends_data import get_stock_trends_data
from app.utils.get_account_balance import get_account_balance
from app.utils.buy_stock import buy_stock
from datetime import datetime, timezone
from app.logger import get_logger

logger = get_logger(__name__)


async def dispatch_tool(name: str, args: dict, news_cache: list) -> str:
    """Route tool call to correct function and return result as string."""
    if name == "get_news":
        result = await get_news()
        news_cache.clear()
        news_cache.extend(result)
        return json.dumps(result)
    elif name == "get_top_movers":
        return json.dumps(await get_top_movers())
    elif name == "get_stock_current_price":
        return json.dumps(await get_stock_current_price(args["symbol"]))
    elif name == "get_stock_historical_data":
        return json.dumps(await get_stock_historical_data(args["symbol"]))
    elif name == "get_stock_trends_data":
        return json.dumps(await get_stock_trends_data(args["symbol"]))
    elif name == "get_account_balance":
        return json.dumps(get_account_balance())
    elif name == "buy_stock":
        result = await buy_stock(
            symbol=args["symbol"],
            amount=args["amount"],
            hold_seconds=args["hold_seconds"],
            kind="SCALP",
            reasoning=args["reasoning"],
            news_at_moment=json.dumps([n["title"] for n in news_cache[:5]]),
            next_trigger_minutes=args.get("next_trigger_minutes", 60),
        )
        return json.dumps(result)
    return json.dumps({"error": f"Unknown tool: {name}"})


async def run_scalp_agent() -> dict:
    """
    Full agentic loop for scalp trading.
    LLM calls tools in any order it wants.
    Returns next_trigger_minutes for scheduler.
    """
    logger.info("Starting scalp agent run...")
    messages = [
        {"role": "system", "content": SCALP_PROMPT},
        {"role": "user", "content": "Market is open. Analyze and decide."},
    ]

    news_cache = []  # shared across tool calls to capture news for logging
    next_trigger_minutes = 60
    traded = False

    for _ in range(10):  # max 10 tool calls per run
        loop = asyncio.get_running_loop()
        call = functools.partial(
            openai_client.chat.completions.create,
            model="gpt-4o-mini",
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
        )
        response = await loop.run_in_executor(None, call)

        msg = response.choices[0].message
        messages.append(msg)

        # No tool calls — LLM is done
        if not msg.tool_calls:
            # LLM decided to skip — log it
            if not traded:
                balance = get_account_balance()
                supabase.table("trades").insert({
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "kind": "SCALP",
                    "action": "SKIP",
                    "reasoning": msg.content or "No reasoning provided",
                    "news_at_moment": json.dumps([n["title"] for n in news_cache[:5]]),
                    "balance_after": balance["balance"],
                    "status": "CLOSED",
                }).execute()
                logger.info(f"[Scalp] Skipped. Reason: {msg.content}")

            return {
                "traded": traded,
                "reasoning": msg.content,
                "next_trigger_minutes": next_trigger_minutes,
            }

        # Process each tool call
        for tool_call in msg.tool_calls:
            name = tool_call.function.name
            args = json.loads(tool_call.function.arguments)

            logger.info(f"[Scalp] Calling tool: {name} with args: {args}")
            result = await dispatch_tool(name, args, news_cache)

            # Capture next_trigger from buy_stock call
            if name == "buy_stock":
                traded = True
                next_trigger_minutes = args.get("next_trigger_minutes", 60)

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": result,
            })

    return {
        "traded": traded,
        "next_trigger_minutes": next_trigger_minutes,
    }