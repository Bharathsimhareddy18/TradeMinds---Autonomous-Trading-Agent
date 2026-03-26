import yfinance as yf
import asyncio
from concurrent.futures import ThreadPoolExecutor
from tenacity import stop_after_attempt, wait_fixed, retry 
from app.logger import get_logger

logger = get_logger(__name__)

STOCK_UNIVERSE = [
    "RELIANCE.NS", "HDFCBANK.NS", "INFY.NS", "TCS.NS", "ICICIBANK.NS",
    "HINDUNILVR.NS", "SBIN.NS", "BHARTIARTL.NS", "ITC.NS", "KOTAKBANK.NS",
    "LT.NS", "AXISBANK.NS", "ASIANPAINT.NS", "MARUTI.NS", "BAJFINANCE.NS",
    "WIPRO.NS", "HCLTECH.NS", "ULTRACEMCO.NS", "TITAN.NS", "SUNPHARMA.NS",
]

@retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
def _fetch_mover(symbol: str) -> dict | None:
    try:
        info = yf.Ticker(symbol).fast_info
        change_pct = ((info.last_price - info.previous_close) / info.previous_close) * 100
        return {
            "symbol": symbol,
            "current_price": round(info.last_price, 2),
            "change_pct": round(change_pct, 2),
        }
    except Exception as e:
        logger.exception(f"Error fetching {symbol}: {e}")
        return None

async def get_top_movers() -> list[dict]:
    """
    Scan stock universe concurrently and return top 10 gainers by % change today.

    Returns:
        list[dict]: Top 10 gainers with symbol, price, and % change.
    """
    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor() as executor:
        tasks = [loop.run_in_executor(executor, _fetch_mover, symbol) for symbol in STOCK_UNIVERSE]
        results = await asyncio.gather(*tasks)

    movers = [r for r in results if r is not None]
    movers.sort(key=lambda x: x["change_pct"], reverse=True)
    return movers[:10]

