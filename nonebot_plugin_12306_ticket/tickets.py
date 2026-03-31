import re
import datetime
from typing import Optional
from nonebot import on_command   # type: ignore
from nonebot.adapters.onebot.v11 import Bot, MessageEvent, MessageSegment, Message
from nonebot.adapters.onebot.v11 import Event
from nonebot.plugin import PluginMetadata  # type: ignore
from nonebot.params import CommandArg, ArgPlainText  # type: ignore
from nonebot.rule import to_me  # type: ignore
from .ticket_details import format_data, get_basic_info
from .telecode import get_telecode, get_station_name
from .get_data import get_12306_remaining_tickets, get_12306_price
from .api import API
from .utils import utils

tickets_info = on_command("车票", aliases={"ticket","tickets"}, priority=5, block=True)
next_page = on_command("下一页", aliases={"next"}, priority=5, block=True)

user_sessions = {}
async def generate_output(current_remaining_data: str,train_date :str,current_index: int) -> Optional[tuple[str, int]]:
    """
    输出模块化
    """
    hr_line = "------------------------------\n"
    output = ""
    ticket_output = ""
    if current_index != 0:
        current_index = current_index + 1
    for data_count in range(current_index,len(current_remaining_data)):
        if data_count <= current_index + 9:

            ticket_details = current_remaining_data[data_count] # 每个列车的余票元数据
            train_id,departure_station_name,terminal_station_name,from_station_name,to_station_name,start_time,end_time,duration = await get_basic_info(ticket_details)
            ticket_price = await get_12306_price(ticket_details,train_date)
            ticket_result = format_data(ticket_details,ticket_price)
            for seat_types, ticket_count in ticket_result.items():
                ticket_output += f"{seat_types}：{ticket_count}\n"
            output += Message([
                f"【{data_count +1}】{train_id}（{departure_station_name}——{terminal_station_name}）\n",
                f"{from_station_name} {start_time} —— {end_time} {to_station_name}，历时{duration}分\n",
                ticket_output,
                hr_line,
            ])
            ticket_output = "" # 重置ticket_output，为下一循环获取车票信息做准备
        else:
            break
    
    return  output, data_count

def content(current_remaining_data): # 翻页有问题
    """
    计算输出结果总页数
    """
    sum_of_result = len(current_remaining_data)
    quotient, remainder = divmod(sum_of_result, 10)
    page_count = quotient + (1 if remainder else 0)
    return page_count

@tickets_info.handle()
async def handle_tickets_info(args: Message = CommandArg(), event: Event = None):
    if user_input := args.extract_plain_text():

        # 处理用户输入
        user_input_separate = user_input.split(" ")
        input_separate_checker = len(user_input_separate)
        if input_separate_checker > 4 or input_separate_checker < 2:
            # await tickets_info.finish("格式错误，请输入车次（可选） 出发站 到达站 日期（可选）") 
            await tickets_info.finish("格式错误，请输入出发站 到达站 日期（可选）") 
        
        train_date = ""
        train_no = ""
        from_station_name_input = ""
        to_station_name_input = ""
        
        for i in range(input_separate_checker):
            current_arg = user_input_separate[i]
            normal_date_match = utils.normal_date_pattern.search(current_arg)
            chinese_date_match = utils.chinese_date_pattern.search(current_arg)
            # train_no_match = utils.train_no_pattern.findall(current_arg)
            
            if normal_date_match or chinese_date_match or "今天" in current_arg or "明天" in current_arg:
                if "今天" in current_arg:
                    train_date = utils.today
                elif "明天" in current_arg:
                    train_date = utils.tomorrow
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

            # elif train_no_match:
            #     train_no = current_arg.upper()

            elif utils.station_name_pattern.match(current_arg):
                if from_station_name_input == "":
                    from_station_name_input = current_arg
                else:
                    to_station_name_input = current_arg
        
        if train_date == "" or train_date < utils.today:
            train_date = utils.today
    
        if not (from_station_name_input and to_station_name_input):
            # await tickets_info.finish("格式错误，请输入车次（可选） 出发站 到达站 日期（可选）")
            await tickets_info.finish("格式错误，请输入 出发站 到达站 日期（可选）") 

        from_station_telecode, to_station_telecode = await get_telecode(from_station_name_input, to_station_name_input)
        if not (from_station_telecode and to_station_telecode):
            await tickets_info.finish("未查询到发站/到站信息，请重新输入")
        # 处理用户数据结束
        
        # 余票数据获取
        response_data = await get_12306_remaining_tickets(train_date, from_station_telecode, to_station_telecode)

        if response_data == "ERR":
            await tickets_info.finish("访问12306出现错误，请稍后再试")
        
        current_remaining_data = response_data['data']['result']

        if not current_remaining_data or len(current_remaining_data) == 0:
            await tickets_info.finish("未查询到符合条件的车次信息")
        
        #数据整合部分与票价获取

        await tickets_info.send("正在加载，请耐心等待...")

        hr_line = "------------------------------\n"
        current_index = 0
        output, data_count = await generate_output(current_remaining_data, train_date, current_index)
        # slice = current_remaining_data
        # test_ouput = await get_12306_price_batch(slice, train_date)
        # testnum = 0
        # while testnum < 10:
        #     print(test_ouput[testnum])
        #     testnum += 1

        user_id = event.get_user_id()
        session_key = event.get_session_id()
        await tickets_info.send(MessageSegment.at(user_id) + "信息如下：\n" + hr_line + output + "---【当前第1页，共"+ str(content(current_remaining_data)) + "页】---\n数据来源：12306.cn")

        if data_count < len(current_remaining_data) -1:
            limit_time_start = datetime.datetime.now().strftime("%Y-%m-%d-%H:%M") # 获取当前时间，在用户激活/下一页 的时候进行时间比对
            user_sessions[session_key] = {
                'data': current_remaining_data,
                'current_index': data_count,
                'train_date': train_date,
                'limit_time_start': datetime.datetime.now(),
                'page': 1
            }
            await tickets_info.finish("如需继续查看，请输入 /下一页，五分钟内有效")
        else:
            await tickets_info.finish()

    else:
        await tickets_info.send("请输入 出发站 到达站 日期（可选）")

@next_page.handle()
async def handle_next_page(event: Event = None):
    user_id = event.get_user_id()
    session_key = event.get_session_id()
    if session_key not in user_sessions:
        await next_page.finish()
    
    session = user_sessions[session_key]
    current_remaining_data = session['data']
    current_index = session['current_index']
    train_date = session['train_date']
    limit_time_start = session['limit_time_start']
    page = session['page'] + 1

    # time1 = datetime.datetime.strptime(limit_time_start, "%Y-%m-%d-%H:%M")
    # time2 = datetime.datetime.strptime(utils.now_time, "%Y-%m-%d-%H:%M")
    # time_diff = abs((time1 - time2).total_seconds())
    # if time_diff > 300: # 五分钟
    #     del user_sessions[session_key] # 清除会话
    #     await next_page.finish()

    # 判断用户是否超时请求 /下一页
    if (datetime.datetime.now() - session["limit_time_start"]).total_seconds() > 300:
        user_sessions.pop(session_key, None)
        await next_page.finish()

    await tickets_info.send("正在加载，请耐心等待...")
    hr_line = "------------------------------\n"
    output, data_count = await generate_output(current_remaining_data, train_date, current_index)
    await next_page.send(MessageSegment.at(user_id) + "信息如下：\n" + hr_line + output + "---【当前第" + str(page) + "页，共"+ str(content(current_remaining_data)) + "页】---\n数据来源：12306.cn")

    if data_count < len(current_remaining_data) -1:
        # limit_time_start = utils.now_time 获取当前时间，在用户激活/下一页 的时候进行时间比对 

        session['current_index'] = data_count
        session['limit_time_start'] = datetime.datetime.now()
        session['page'] = page
        await next_page.finish("如需继续查看，请输入 /下一页，五分钟内有效")
    else:
        user_sessions.pop(session_key, None) # 清除会话
        await next_page.finish()