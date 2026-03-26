from tenacity import wait_fixed
import yfinance as yf
import asyncio
from concurrent.futures import ThreadPoolExecutor
from tenacity import stop_after_attempt, wait_fixed, wait_fixed, retry

@retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
def _fetch_historical(symbol: str, days: int) -> dict:
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period=f"{days}d")

        closes = [round(c, 2) for c in hist["Close"].tolist()]
        dates = [str(d.date()) for d in hist.index.tolist()]

        return {
            "symbol": symbol,
            "days": days,
            "dates": dates,
            "closing_prices": closes,
        }
    except Exception as e:
        print(f"Error fetching historical data for {symbol}: {e}")
        return {"symbol": symbol, "error": str(e)}

@retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
async def get_stock_historical_data(symbol: str, days: int = 30) -> dict:
    """
    Fetch historical closing prices for a given NSE stock.

    Args:
        symbol (str): NSE symbol e.g. RELIANCE.NS
        days (int): Number of days of history to fetch (default 30)

    Returns:
        dict: symbol, dates, closing prices
    """
    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor() as executor:
        result = await loop.run_in_executor(executor, _fetch_historical, symbol, days)
    return result


if __name__ == "__main__":
    result = asyncio.run(get_stock_historical_data("RELIANCE.NS"))
    print(result)