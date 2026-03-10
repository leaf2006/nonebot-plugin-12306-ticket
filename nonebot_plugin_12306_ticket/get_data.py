import httpx
import re
import urllib3
import asyncio
from .api import API
from typing import Optional

async def get_12306_remaining_tickets(train_date :str, from_station_telecode :str, to_station_telecode :str) -> Optional[str]:
    """
    获取12306余票数据
    """

    params = { # 输入数据
        "leftTicketDTO.train_date": train_date,
        "leftTicketDTO.from_station": from_station_telecode,
        "leftTicketDTO.to_station": to_station_telecode,
        "purpose_codes": "ADULT"
    }

    # init_url = API.init_url
    try:
        async with httpx.AsyncClient() as client:
            init_response = await client.get(API.init_url)
            query_url_match = re.search(r"'queryUrl':\s*'([^']+)'", init_response.text)
            if not query_url_match:
                query_url_match = re.search(r"leftTicket/query[A-Z]", init_response.text)
            
            if query_url_match:
                query_url = query_url_match.group(0) if len(query_url_match.groups()) == 0 else query_url_match.group(1)
                ticket_query_url = f"{API.ticket_query_url}{query_url}"
            else:
                ticket_query_url = f"{API.ticket_query_url}leftTicket/query"

            response = await client.get(ticket_query_url, params=params)
            if "error.html" in str(response.url):
                return "ERR"
            
            return response.json() # TODO


    except Exception as e:
        return "ERR"

# async def get_12306_price(train_unique_id :str, from_station_no :str, to_station_no :str, seat_types_raw :str,train_date :str) -> Optional[str]:
async def get_12306_price(raw_data: str, train_date :str) -> Optional[str]:
    """
    获取12306票价信息
    """

    p = raw_data.split('|')
    train_unique_id = p[2]
    from_station_no = p[16]
    to_station_no = p[17]
    seat_types = p[34].replace("0","")


    # seat_types = seat_types_raw.replace("0","")

    params = {
        "train_no": train_unique_id,
        "from_station_no": from_station_no,
        "to_station_no": to_station_no,
        "seat_types": seat_types,
        "train_date": train_date
    }

    try:
        async with httpx.AsyncClient() as client:
            init_response = await client.get(API.init_url)

            response = await client.get(API.ticket_price_url, params=params)
            
            if "error.html" in str(response.url):
                return "ERR"
            
            return response.json()
        
    except Exception as e:
        return "ERR"
