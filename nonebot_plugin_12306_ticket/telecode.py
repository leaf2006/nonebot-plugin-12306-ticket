import httpx
from pyreqwest.client import ClientBuilder
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
        # async with httpx.AsyncClient() as client:
        async with ClientBuilder().build() as client:
            response = await client.get(url).headers(API.headers).build().send()
            # response = await client.get(url, headers=API.headers)
            # station_data = response.text
            station_data = await response.text()
            pattern = r"@[^|]*\|([^|]+)\|([^|]+)\|[^|]*" # 圆括号 () 表示捕获组，只有被括号包围的部分才会被 re.findall() 提取，没有括号的部分 只用于匹配定位，但不会出现在结果中
            matches = re.findall(pattern,station_data)
            station_map = {name: code for name, code in matches}

            from_station_telecode = station_map.get(from_station_name, None)
            to_station_telecode = station_map.get(to_station_name, None)

            return from_station_telecode, to_station_telecode
    
    except Exception:
        return None,None
    
async def get_station_name(from_station_telecode: str, to_station_telecode: str) -> Optional[tuple[str, str]]:
    """
    通过出发站、到达站的铁路电报码获取车站中文名称
    """
    url = API.telecode_url
    try:
        async with ClientBuilder().build() as client:
            # response = await client.get(url, headers=API.headers)
            response = await client.get(url).headers(API.headers).build().send()
            # station_data = response.text
            station_data = await response.text()
            pattern = r"@[^|]*\|([^|]+)\|([^|]+)\|[^|]*"
            matches = re.findall(pattern, station_data)
            # 创建电报码到车站名的映射（反转映射）
            telecode_map = {code: name for name, code in matches}

            from_station_name = telecode_map.get(from_station_telecode, None)
            to_station_name = telecode_map.get(to_station_telecode, None)

            return from_station_name, to_station_name

    except Exception:
        return None, None