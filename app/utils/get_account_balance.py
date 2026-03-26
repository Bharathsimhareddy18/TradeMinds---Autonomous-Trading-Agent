from app.config import supabase
from tenacity import stop_after_attempt, wait_fixed, retry  

@retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
def get_account_balance() -> dict:
    """
    Fetch current account balance and stats from DB.

    Returns:
        dict: balance, total_trades, total_pnl, wins, losses, win_rate
    """
    account = supabase.table("account").select("*").eq("id", 1).execute().data[0]

    total_trades = account["total_trades"]
    wins = account["wins"]

    return {
        "balance": float(account["balance"]),
        "total_trades": total_trades,
        "total_pnl": float(account["total_pnl"]),
        "wins": wins,
        "losses": account["losses"],
        "win_rate": round((wins / total_trades * 100), 1) if total_trades > 0 else 0.0,
    }
    
print(get_account_balance())