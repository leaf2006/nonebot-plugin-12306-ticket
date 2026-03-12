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
from .ticket_details import format_data, get_basic_info
from .telecode import get_telecode, get_station_name
from .get_data import get_12306_remaining_tickets, get_12306_price
from .api import API

tickets_info = on_command("车票", aliases={"cp","ticket","tickets"}, priority=5, block=True)
@tickets_info.handle()
async def handle_tickets_info(args: Message = CommandArg(), event: Event = None):
    if user_input := args.extract_plain_text():

        # 处理用户输入
        user_input_separate = user_input.split(" ")
        input_separate_checker = len(user_input_separate)
        if input_separate_checker > 4 or input_separate_checker < 2:
            # await tickets_info.finish("格式错误，请输入车次（可选） 出发站 到达站 日期（可选）") 
            await tickets_info.finish("格式错误，请输入车次 出发站 到达站 日期（可选）") # TODO
            return
        
        normal_date_pattern = re.compile(r'\d{4}-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])')
        chinese_date_pattern = re.compile(r'\d{4}年([1-9]|1[0-2])月([1-9]|[12]\d|3[01])日')
        train_no_pattern = re.compile(r'[A-Za-z]\d{1,4}|\d{4}') 
        station_name_pattern = re.compile(r'^[\u4e00-\u9fff]+$')
        today = datetime.date.today().strftime("%Y-%m-%d")
        tomorrow = (datetime.date.today() + datetime.timedelta(days=1)).strftime("%Y-%m-%d")

        train_date = ""
        train_no = ""
        from_station_name_input = ""
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
                if from_station_name_input == "":
                    from_station_name_input = current_arg
                else:
                    to_station_name = current_arg
        
        if train_date == "" or train_date < today:
            train_date = today
    
        if not from_station_name_input or not to_station_name:
            # await tickets_info.finish("格式错误，请输入车次（可选） 出发站 到达站 日期（可选）")
            await tickets_info.finish("格式错误，请输入 出发站 到达站 日期（可选）") # TODO
            return

        from_station_telecode, to_station_telecode = await get_telecode(from_station_name_input, to_station_name)
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

        await tickets_info.send("正在加载，请耐心等待...")

        output = ""
        ticket_output = ""
        hr_line = "------------------------------\n"
        for data_count in range(len(current_remaining_data)):
            if data_count < 10:

                ticket_details = current_remaining_data[data_count] # 每个列车的余票元数据
                train_id,departure_station_name,terminal_station_name,from_station_name,to_station_name,start_time,end_time,duration = await get_basic_info(ticket_details)
                ticket_price = await get_12306_price(ticket_details,train_date)
                ticket_result = format_data(ticket_details,ticket_price)
                for seat_types, ticket_count in ticket_result.items():
                    ticket_output += f"{seat_types}：{ticket_count}\n"
                output += Message ([
                     f"【{data_count +1}】{train_id}（{departure_station_name}——{terminal_station_name}）\n",
                    f"{from_station_name} {start_time} —— {end_time} {to_station_name}，历时{duration}分\n",
                    ticket_output,
                    hr_line,
                ])
                ticket_output = ""

            else:
                break

        user_id = event.get_user_id()
        await tickets_info.finish(MessageSegment.at(user_id) + "信息如下：\n" + hr_line + output + "若结果过多，只会仅显示前10条结果\n数据来源：12306.cn")
        # print(response_data)
    
    else:
        await tickets_info.finish("请输入 出发站 到达站 日期（可选）")