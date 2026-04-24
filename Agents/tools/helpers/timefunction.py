from datetime import datetime
from agents import function_tool

@function_tool
async def get_time():
    return f"Heute ist {datetime.now().strftime('%A, der %d.%m.%Y')} und es ist {datetime.now().strftime('%H:%M:%S')} Uhr."