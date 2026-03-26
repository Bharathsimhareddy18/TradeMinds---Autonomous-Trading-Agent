import yfinance as yf
import asyncio
from concurrent.futures import ThreadPoolExecutor
from tenacity import stop_after_attempt, wait_fixed, retry
from app.logger import get_logger

logger = get_logger(__name__)

@retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
def _fetch_price(symbol: str) -> dict:
    try:
        info = yf.Ticker(symbol).fast_info
        change_pct = ((info.last_price - info.previous_close) / info.previous_close) * 100
        return {
            "symbol": symbol,
            "current_price": round(info.last_price, 2),
            "change_pct": round(change_pct, 2),
            "open": round(info.open, 2),
            "day_high": round(info.day_high, 2),
            "day_low": round(info.day_low, 2),
            "volume": int(info.three_month_average_volume or 0),
        }
    except Exception as e:
        logger.exception(f"Error fetching {symbol}: {e}")
        return {"symbol": symbol, "error": str(e)}

@retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
async def get_stock_current_price(symbol: str) -> dict:
    """
    Fetch current price snapshot for a given NSE stock.

    Args:
        symbol (str): NSE symbol e.g. RELIANCE.NS

    Returns:
        dict: current price, % change, open, high, low, volume
    """
    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor() as executor:
        result = await loop.run_in_executor(executor, _fetch_price, symbol)
    return result

