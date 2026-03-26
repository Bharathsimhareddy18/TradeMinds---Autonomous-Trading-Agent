from datetime import datetime
from zoneinfo import ZoneInfo

def get_current_time_in_timezone(timezone: str) -> str:
    """
    Get the current time in the specified timezone.

    Args:
        timezone (str): The timezone to get the current time for (e.g., 'America/New_York').  
       
    returns:
        str: The current time in the specified timezone formatted as 'YYYY-MM-DD HH:MM:SS'. 
    """
        
    ist_time = datetime.now(ZoneInfo(timezone))
    
    return ist_time.strftime('%Y-%m-%d %H:%M:%S')

