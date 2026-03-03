import httpx
import json
import urllib3
import re
import datetime
from nonebot import on_command   # type: ignore
from nonebot.adapters.onebot.v11 import Message, MessageSegment   # type: ignore
from nonebot.plugin import PluginMetadata  # type: ignore
from nonebot.params import CommandArg  # type: ignore
from nonebot.rule import to_me  # type: ignore
# from .utils import utils
from .get_telecode import get_telecode
from .api import API

tickets_info = on_command("车票", aliases={"cp","ticket","tickets"}, priority=5, block=True)

def parse_train_data(data_string):
    p = data_string.split('|')
    
    train_result = {
        "train_no": p[3],
        "start_time": p[8],
        "end_time": p[9],
        "duration": p[10],
        "date": p[13],
        "seat_types": p[34],
        "tickets": {
            "二等座": p[30] if p[30] else "--",
            "一等座": p[31] if p[31] else "--",
            "商务座": p[32] if p[32] else "--",
            "动卧": p[33] if p[33] else "--",
            "硬座": p[29] if p[29] else "--",
            "软座": p[23] if p[23] else "--",
            "硬卧": p[28] if p[28] else "--",
            "软卧": p[23] if p[23] else "--",
            "高级软卧": p[21] if p[21] else "--",
            "无座": p[26] if p[26] else "--"
        }
    }
    return train_result

@tickets_info.handle()
async def handle_tickets_info(args: Message = CommandArg()):
    if user_input := args.extract_plain_text():

        user_input_separate = user_input.split(" ")
        input_separate_checker = len(user_input_separate)
        if input_separate_checker > 4 or input_separate_checker < 2:
            await tickets_info.finish("格式错误，请输入车次（可选） 出发站 到达站 日期（可选）")
            return
        
        normal_date_pattern = re.compile(r'\d{4}-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])')
        chinese_date_pattern = re.compile(r'\d{4}年([1-9]|1[0-2])月([1-9]|[12]\d|3[01])日')
        train_no_pattern = re.compile(r'[A-Za-z]\d{1,4}|\d{4}') 
        station_name_pattern = re.compile(r'^[\u4e00-\u9fff]+$')
        today = datetime.date.today().strftime("%Y-%m-%d")
        tomorrow = (datetime.date.today() + datetime.timedelta(days=1)).strftime("%Y-%m-%d")

        train_date = ""
        train_no = ""
        from_station_name = ""
        to_station_name = ""
        
        for i in range(input_separate_checker):
            current_arg = user_input_separate[i]
            normal_date_match = normal_date_pattern.search(current_arg)
            chinese_date_match = chinese_date_pattern.search(current_arg)
            train_no_match = train_no_pattern.findall(current_arg)
            
            if normal_date_match or chinese_date_match or "今天" in current_arg or "明天" in current_arg:
                if "今天" in current_arg:
                    train_date = today
                elif "明天" in current_arg:
                    train_date = tomorrow
                else:
                    if normal_date_match:
                        year = normal_date_match.group(0)[:4]
                        month = normal_date_match.group(1)
                        day = normal_date_match.group(2)
                    elif chinese_date_match:
                        year = chinese_date_match.group(0)[:4]
                        month = chinese_date_match.group(1)
                        day = chinese_date_match.group(2)
                    train_date = f"{year}-{month.zfill(2)}-{day.zfill(2)}"

            elif train_no_match:
                train_no = current_arg.upper()

            elif station_name_pattern.match(current_arg):
                if from_station_name == "":
                    from_station_name = current_arg
                else:
                    to_station_name = current_arg
        
        if train_date == "" or train_date < today:
            train_date = today
    
        if not from_station_name or not to_station_name:
            await tickets_info.finish("格式错误，请输入车次（可选） 出发站 到达站 日期（可选）")
            return

        from_station_telecode, to_station_telecode = await get_telecode(from_station_name, to_station_name)
        if from_station_telecode is None or to_station_telecode is None:
            await tickets_info.finish("未查询到发站/到站信息，请重新输入")
            return
        
        params = {
            "leftTicketDTO.train_date": train_date,
            "leftTicketDTO.from_station": from_station_telecode,
            "leftTicketDTO.to_station": to_station_telecode,
            "purpose_codes": "ADULT"
        }

        async with httpx.AsyncClient(headers=API.headers, verify=False, timeout=30.0) as client:
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
            
            response_text = response.text
            
            if not response_text or len(response_text.strip()) < 10:
                ticket_advance_sale_days = (datetime.date.today() + datetime.timedelta(days=15)).strftime("%Y-%m-%d")
                if train_date >= ticket_advance_sale_days:
                    await tickets_info.finish("未获取到任何数据，可能是车票未到预售期，请选择其他日期")
                else: 
                    await tickets_info.finish("未获取到任何数据，请检查查询条件或稍后再试")
                return
            
            if "error.html" in str(response.url) or "error" in response_text.lower():
                await tickets_info.finish("出现错误，Bot 被 12306 禁止访问，请稍后再试！")
                return
            
            try:
                response_data = response.json()
            except json.JSONDecodeError as e:
                await tickets_info.finish("发生错误：str(error)")
                # await tickets_info.finish(f"响应数据格式错误：接口可能返回了非 JSON 数据。\n错误信息：{str(e)}\n响应内容前 100 字符：{response_text[:100]}")
                return
            
            # if not isinstance(response_data, dict):
            #     await tickets_info.finish(f"响应数据类型错误：期望字典类型，实际为 {type(response_data).__name__}")
            #     return
            
            # if response_data.get('status') is False:
            #     error_message = response_data.get('messages', ['URL 验证失败，请稍后再试'])[0]
            #     await tickets_info.finish(f"查询失败：{error_message}")
            #     return
            
            # if 'data' not in response_data:
            #     await tickets_info.finish(f"查询失败：响应数据结构错误\n完整响应：{str(response_data)[:200]}")
            #     return
            
            # if 'result' not in response_data['data']:
            #     await tickets_info.finish("未查询到符合条件的车次信息")
            #     return
            
            current_data = response_data['data']['result']
            
            if not current_data or len(current_data) == 0:
                await tickets_info.finish("未查询到符合条件的车次信息")
                return
            
            output = ""
            hr_line = "------------------------------ \n"
            for data_count in range(len(current_data)):
                if data_count < 10:
                    result = parse_train_data(current_data[data_count])
                    tickets_result = result['tickets']
                    output += f"【{str(data_count +1)}】车次：{result['train_no']}\n"
                    for ticket_type, ticket_count in tickets_result.items():
                        if ticket_count == "--":
                            continue
                        else:
                            output += f"{ticket_type}：{ticket_count}\n"
                    output += hr_line
                else:
                    break
            
            if output == "":
                await tickets_info.finish("未查询到符合条件的车次信息")
                return
            
            await tickets_info.finish(output)

    else:
        await tickets_info.finish("请输入车次（可选） 出发站 到达站 日期（可选）")