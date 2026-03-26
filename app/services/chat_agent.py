# app/services/chat_agent.py

import json
from app.config import openai_client, supabase
from app.prompts import CHAT_PROMPT


def get_trade_context() -> dict:
    """Fetch recent trades and account stats for LLM context."""
    recent_trades = supabase.table("trades") \
        .select("*") \
        .order("timestamp", desc=True) \
        .limit(30) \
        .execute().data

    account = supabase.table("account") \
        .select("*") \
        .eq("id", 1) \
        .execute().data[0]

    return {
        "account": account,
        "recent_trades": recent_trades,
    }


async def run_chat_agent(question: str) -> str:
    """
    Answer natural language questions about trade history.

    Args:
        question (str): User's question e.g. 'Why did you buy Reliance yesterday?'

    Returns:
        str: LLM answer based on trade history
    """
    context = get_trade_context()

    user_message = f"""
User Question: {question}

Account Stats:
{json.dumps(context["account"], default=str)}

Recent Trades (last 30):
{json.dumps(context["recent_trades"], default=str)}
"""

    response = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": CHAT_PROMPT},
            {"role": "user", "content": user_message},
        ],
    )

    return response.choices[0].message.content