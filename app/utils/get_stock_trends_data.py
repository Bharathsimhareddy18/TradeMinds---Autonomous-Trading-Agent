from tenacity import wait_fixed
import yfinance as yf
import asyncio
from concurrent.futures import ThreadPoolExecutor
from tenacity import stop_after_attempt, wait_fixed, wait_fixed, retry


@retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
def _fetch_trends(symbol: str) -> dict:
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="10d")
        closes = [round(c, 2) for c in hist["Close"].tolist()]

        if len(closes) < 2:
            return {"symbol": symbol, "error": "Not enough data"}

        # Count consecutive up days from most recent
        consecutive_up_days = 0
        for i in range(len(closes) - 1, 0, -1):
            if closes[i] > closes[i - 1]:
                consecutive_up_days += 1
            else:
                break

        # 5 day average
        five_day_avg = round(sum(closes[-5:]) / 5, 2)
        current_price = closes[-1]
        above_5day_avg = current_price > five_day_avg

        # % change over last 5 days
        change_5d = round(((closes[-1] - closes[-5]) / closes[-5]) * 100, 2)

        # Trend direction
        if consecutive_up_days >= 2 and above_5day_avg:
            trend = "BULLISH"
        elif consecutive_up_days == 0:
            trend = "BEARISH"
        else:
            trend = "NEUTRAL"

        return {
            "symbol": symbol,
            "current_price": current_price,
            "consecutive_up_days": consecutive_up_days,
            "five_day_avg": five_day_avg,
            "above_5day_avg": above_5day_avg,
            "change_5d_pct": change_5d,
            "trend": trend,
        }
    except Exception as e:
        print(f"Error fetching trends for {symbol}: {e}")
        return {"symbol": symbol, "error": str(e)}


@retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
async def get_stock_trends_data(symbol: str) -> dict:
    """
    Fetch trend analysis for a given NSE stock.

    Args:
        symbol (str): NSE symbol e.g. RELIANCE.NS

    Returns:
        dict: trend direction, consecutive up days, 5 day average, % change
    """
    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor() as executor:
        result = await loop.run_in_executor(executor, _fetch_trends, symbol)
    return result

