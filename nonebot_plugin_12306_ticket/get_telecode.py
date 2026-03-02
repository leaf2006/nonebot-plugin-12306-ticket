import httpx
import re
import asyncio
from .api import API
from typing import Optional

async def get_telecode(from_station_name :str , to_station_name :str) -> Optional[tuple[str, str]]:
    """
    获取出发站、到达站的铁路电报码
    """
    url = API.telecode_url
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url,headers=API.headers)
            station_data = response.text
            pattern = r"@[^|]*\|([^|]+)\|([^|]+)\|[^|]*" # 圆括号 () 表示捕获组，只有被括号包围的部分才会被 re.findall() 提取，没有括号的部分 只用于匹配定位，但不会出现在结果中
            matches = re.findall(pattern,station_data)
            station_map = {name: code for name, code in matches}

            from_station_telecode = station_map.get(from_station_name, None)
            to_station_telecode = station_map.get(to_station_name, None)

            return from_station_telecode, to_station_telecode
    
    except Exception:
        return None,None