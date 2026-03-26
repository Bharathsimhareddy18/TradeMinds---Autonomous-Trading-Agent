import feedparser
from tenacity import stop_after_attempt, wait_fixed, wait_fixed, retry

KEYWORDS = [
    "stock", "share", "NSE", "BSE", "Nifty", "Sensex",
    "market", "rally", "fall", "earnings", "IPO", "trade",
    "equity", "invest", "rupee", "profit", "loss", "quarterly"
]
@retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
async def get_news() -> list[dict]:
    """
    Fetch latest Indian stock market news from RSS feeds.

    Returns:
        list[dict]: List of articles with title, source, and published time.
    """
    feeds = [
        {"url": "https://economictimes.indiatimes.com/markets/stocks/rssfeeds/2146842.cms", "source": "Economic Times"},
        {"url": "https://feeds.feedburner.com/ndtvprofit-latest", "source": "NDTV Profit"},
        {"url": "https://www.livemint.com/rss/markets", "source": "Livemint"},
        {"url": "https://www.business-standard.com/rss/markets-106.rss", "source": "Business Standard"}
    ]

    articles = []

    for feed in feeds:
        try:
            parsed = feedparser.parse(feed["url"])
            for entry in parsed.entries[:5]:
                title = entry.title
                if any(keyword.lower() in title.lower() for keyword in KEYWORDS):
                    articles.append({
                        "title": title,
                        "source": feed["source"],
                        "published_at": entry.get("published", "N/A"),
                    })
        except Exception as e:
            print(f"Error fetching {feed['source']}: {e}")
            continue

    return articles
