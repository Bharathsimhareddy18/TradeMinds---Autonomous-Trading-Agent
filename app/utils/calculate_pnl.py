def calculate_pnl(entry_price: float, exit_price: float, amount_invested: float) -> dict:
    """
    Calculate profit or loss for a paper trade.

    Args:
        entry_price (float): Price at which stock was bought.
        exit_price (float): Price at which stock was sold.
        amount_invested (float): Total amount invested in INR.

    Returns:
        dict: units, pnl, pnl_pct, result
    """
    units = amount_invested / entry_price
    pnl = (exit_price - entry_price) * units
    pnl_pct = ((exit_price - entry_price) / entry_price) * 100

    return {
        "units": round(units, 4),
        "pnl": round(pnl, 2),
        "pnl_pct": round(pnl_pct, 2),
        "result": "WIN" if pnl > 0 else "LOSS" if pnl < 0 else "BREAKEVEN",
    }


