
from app.config import settings

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_news",
            "description": "Fetch latest Indian stock market news headlines from RSS feeds. Always call this first.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_top_movers",
            "description": "Get top 10 NSE stocks gaining the most today by % change.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_stock_current_price",
            "description": "Get live price snapshot for a specific NSE stock — current price, % change, open, high, low, volume.",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "NSE symbol e.g. RELIANCE.NS",
                    },
                },
                "required": ["symbol"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_stock_historical_data",
            "description": "Get last 30 days closing prices for a stock to understand price movement over time.",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "NSE symbol e.g. RELIANCE.NS",
                    },
                },
                "required": ["symbol"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_stock_trends_data",
            "description": "Get trend analysis for a stock — consecutive up days, 5 day average, BULLISH/BEARISH/NEUTRAL signal.",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "NSE symbol e.g. RELIANCE.NS",
                    },
                },
                "required": ["symbol"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_account_balance",
            "description": "Get current fake balance, total P&L, win rate. Always check this before trading.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "buy_stock",
            "description": (
                "Execute a paper trade. Records entry price, waits hold_seconds, "
                "records exit price, calculates P&L, updates balance in DB."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "NSE symbol e.g. RELIANCE.NS",
                    },
                    "amount": {
                        "type": "number",
                        "description": f"Amount in INR to invest. Min ₹{int(settings.MIN_TRADE)}, Max ₹{int(settings.MAX_SCALP_TRADE)}",
                    },
                    "hold_seconds": {
                        "type": "integer",
                        "description": f"How long to hold in seconds. Min {settings.TRADE_WINDOW_MIN_SECONDS}, Max {settings.TRADE_WINDOW_MAX_SECONDS}",
                    },
                    "reasoning": {
                        "type": "string",
                        "description": "Why you are making this trade. Be specific — this gets logged.",
                    },
                    "next_trigger_minutes": {
                        "type": "integer",
                        "description": "When should scalp agent wake up next (5 to 1440 minutes).",
                    },
                },
                "required": ["symbol", "amount", "hold_seconds", "reasoning", "next_trigger_minutes"],
            },
        },
    },
]