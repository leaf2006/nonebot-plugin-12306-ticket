# import httpx
# import json
# import urllib3
import re
import datetime
from nonebot import on_command   # type: ignore
from nonebot.adapters.onebot.v11 import Bot, MessageEvent, MessageSegment, Message
from nonebot.adapters.onebot.v11 import Event
from nonebot.plugin import PluginMetadata  # type: ignore
from nonebot.params import CommandArg  # type: ignore
from nonebot.rule import to_me  # type: ignore
from .ticket_details import parse_train_data, format_data
from .get_telecode import get_telecode
from .get_data import get_12306_remaining_tickets, get_12306_price
from .api import API

tickets_info = on_command("车票", aliases={"cp","ticket","tickets"}, priority=5, block=True)

# def parse_train_data(data_string):
#     p = data_string.split('|')
    
#     train_result = {
#         "train_no": p[3],
#         "start_time": p[8],
#         "end_time": p[9],
#         "duration": p[10],
#         "date": p[13],
#         "seat_types": p[34],
#         "tickets": {
#             "二等座": p[30] if p[30] else "--",
#             "一等座": p[31] if p[31] else "--",
#             "商务座": p[32] if p[32] else "--",
#             "动卧": p[33] if p[33] else "--",
#             "硬座": p[29] if p[29] else "--",
#             "软座": p[23] if p[23] else "--",
#             "硬卧": p[28] if p[28] else "--",
#             "软卧": p[23] if p[23] else "--",
#             "高级软卧": p[21] if p[21] else "--",
#             "无座": p[26] if p[26] else "--"
#         }
#     }
#     return train_result

@tickets_info.handle()
async def handle_tickets_info(args: Message = CommandArg(), event: Event = None):
    if user_input := args.extract_plain_text():

        # 处理用户输入
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
        # 处理用户数据结束
        
        # 余票数据获取
        response_data = await get_12306_remaining_tickets(train_date, from_station_telecode, to_station_telecode)

        if response_data == "ERR":
            await tickets_info.finish("访问12306出现错误，请稍后再试")
            return
        
        current_remaining_data = response_data['data']['result']

        if not current_remaining_data or len(current_remaining_data) == 0:
            await tickets_info.finish("未查询到符合条件的车次信息")
            return
        
        #数据整合部分与票价获取

        await tickets_info.send("正在加载数据，请稍候...")

        output = ""
        hr_line = "------------------------------\n"
        for data_count in range(len(current_remaining_data)):
            if data_count < 10:

                ticket_details = current_remaining_data[data_count] # 每个列车的余票元数据
                ticket_price = await get_12306_price(ticket_details,train_date)
                result = format_data(ticket_details,ticket_price)
                print(result)

                # ticket_price_format_normal = format_pricesystem(ticket_price)
                # print(ticket_price)
                # print(ticket_price_format_normal)

            else:
                break
        # user_id = event.get_user_id()
        # await tickets_info.finish(MessageSegment.at(user_id) + "信息如下：\n" + output)
        # print(response_data)