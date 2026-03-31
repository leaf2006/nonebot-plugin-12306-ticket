from nonebot import on_command
from nonebot.params import CommandArg, ArgPlainText  # type: ignore
from nonebot.adapters.onebot.v11 import MessageEvent, Bot, MessageSegment, Message
from nonebot import require
from typing import Optional
import datetime
from .get_data import get_12306_remaining_tickets,get_12306_price
from .telecode import get_telecode, get_station_name
from .ticket_details import time_filter, format_data, get_basic_info, time_range_output
from .utils import utils

require("nonebot_plugin_apscheduler")
from nonebot_plugin_apscheduler import scheduler # type: ignore

scheduled_query = on_command("定时查询", priority=5, block=True)
cancel_scheduled_query = on_command("取消查询",aliases={"结束查询"} ,priority=5, block=True)

# 存储每个用户的计数
user_counts = {}  # {user_id: 当前第几次}
user_sessions = {}

async def generate_output(current_remaining_data :str, train_date :str) -> Optional[tuple[str, str]]:
    """
    查询余票并输出模块化
    """
    hr_line = "------------------------------\n"
    ticket_info_output = ""
    ticket_output = ""
    ticket_avaliable_count = 0
    # 标记是否有超过10趟有票车次（仅展示前10趟）
    more_tickets = False
    for data_count in range(len(current_remaining_data)):
        ticket_details = current_remaining_data[data_count]
        split_remaining_data = ticket_details.split('|')
        # 每趟车都重新判断一次，避免沿用上一趟的有票状态
        ticket_avaliable = False
        pending_test_seat_types = [30,31,32,33,29,23,28,21,26]
        for test_seat_types in pending_test_seat_types:
            remaining_ticket = split_remaining_data[test_seat_types]
            if remaining_ticket != "无" and remaining_ticket != "*" and remaining_ticket != "" and remaining_ticket != None: # 增加*,标*的是未开售车票
                ticket_avaliable = True
                break
        
        if ticket_avaliable == True:
            ticket_avaliable_count += 1
            if ticket_avaliable_count > 10:
                more_tickets = True
                break

            train_id,departure_station_name,terminal_station_name,from_station_name,to_station_name,start_time,end_time,duration = await get_basic_info(ticket_details)
            ticket_price = await get_12306_price(ticket_details, train_date)
            ticket_result = format_data(ticket_details, ticket_price)
            for seat_types, ticket_count in ticket_result.items():
                ticket_output += f"{seat_types}：{ticket_count}\n"
            ticket_info_output += Message ([
                f"【{ticket_avaliable_count}】{train_id}（{departure_station_name}——{terminal_station_name}）\n",
                f"{from_station_name} {start_time} —— {end_time} {to_station_name}，历时{duration}分\n",
                ticket_output,
                hr_line,
            ])
            ticket_output = "" # 重置
    
    if ticket_avaliable_count == 0:
        return "","no_tickets"
    elif more_tickets == False:
        return str(ticket_info_output),"ten_or_less"
    elif more_tickets == True:
        return str(ticket_info_output),"over_ten"

def cleanup_session(session_key):
    """
    清理模块化
    """
    scheduler.remove_job(f"query_timer_{session_key}")
    user_counts.pop(session_key, None)
    user_sessions.pop(session_key,None)

@scheduled_query.handle()
async def handle_timer(bot: Bot, event: MessageEvent, args: Message = CommandArg()):

    none_input_alert = Message([
        "请输入出发站 到达站 出发日期（可选） 列车出发时间范围（可选） 持续查询时间间隔\n",
        "示例：/定时查询 湖州 厦门北 2026-03-25 14-16 10分钟\n",
        "（每10分钟查询一次2026年3月25日 14时到16时之间 湖州 开往 厦门北 的所有列车是否有余票）\n",
    ])

    if user_input := args.extract_plain_text():
        user_input_separate = user_input.split(' ')
        input_separate_checker = len(user_input_separate)
        if input_separate_checker > 5 or input_separate_checker < 3:
            await scheduled_query.finish(none_input_alert)
        
        train_date = ""
        from_station_name_input = ""
        to_station_name_input = ""
        range_start_time = ""
        range_end_time = ""
        # 时间范围为可选参数，先给默认值，避免后续未定义
        range_start_time_raw = ""
        range_end_time_raw = ""

        for i in range(input_separate_checker):
            current_arg = user_input_separate[i]
            normal_date_match = utils.normal_date_pattern.search(current_arg)
            chinese_date_match = utils.chinese_date_pattern.search(current_arg)
            departure_time_range_match = utils.departure_time_range_pattern.search(current_arg)
            scheduled_query_match = utils.scheduled_query_pattern.search(current_arg)

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
            elif utils.station_name_pattern.match(current_arg):
                if from_station_name_input == "":
                    from_station_name_input = current_arg
                else:
                    to_station_name_input = current_arg
            elif departure_time_range_match:
                range_start_time_raw = departure_time_range_match.group(1) # 起始时间（小时）
                range_end_time_raw = departure_time_range_match.group(2) # 终止时间（小时）
                range_start_time = datetime.datetime.strptime(f'{int(range_start_time_raw):02}:00', '%H:%M')
                range_end_time = datetime.datetime.strptime(f'{int(range_end_time_raw):02}:00', '%H:%M')
            elif scheduled_query_match:
                scheduled_query_time_raw = scheduled_query_match.group(1)
                scheduled_query_unit = scheduled_query_match.group(2) # 捕获单位（小时、分钟）
                if scheduled_query_unit == "小时":
                    scheduled_query_time = int(scheduled_query_time_raw) *60 # 转化为分钟
                else:
                    scheduled_query_time = int(scheduled_query_time_raw)

        if train_date == "" or train_date < utils.today:
            train_date = utils.today 

        # 用户输入了时间范围时，要求结束时间必须晚于开始时间
        if range_start_time and range_end_time and range_end_time <= range_start_time:
            await scheduled_query.finish("时间范围输入错误：结束时间必须大于起始时间")
        # 获取并格式化用户输入结束
    
        # 处理部分错误
        if not (from_station_name_input and to_station_name_input):
            await scheduled_query.finish(none_input_alert)
        from_station_telecode ,to_station_telecode = await get_telecode(from_station_name_input, to_station_name_input)
        if not (from_station_telecode and to_station_telecode):
            await scheduled_query.finish(none_input_alert)
        
        response_data = await get_12306_remaining_tickets(train_date, from_station_telecode, to_station_telecode)
        if response_data == "ERR":
            await scheduled_query.finish("访问12306出现错误，请稍后再试")
        current_remaining_data = response_data['data']['result']
        if not current_remaining_data or len(current_remaining_data) == 0:
            await scheduled_query.finish("未查询到符合条件的车次信息")
        # 处理错误结束

        filtered_remaining_data = time_filter(current_remaining_data, range_start_time, range_end_time) # 根据时间筛选数据

        # 查询并输出
        enable_scheduled_query = False
        ticket, status = await generate_output(filtered_remaining_data, train_date)
        range_time_message = time_range_output(range_start_time_raw, range_end_time_raw)
        if status == "no_tickets":
            output_message = Message ([
                "❌抱歉，您查询的",from_station_name_input,"到",to_station_name_input,"，",range_time_message,"暂时无票\n",
                str(scheduled_query_time_raw),str(scheduled_query_unit),"后将再次查询",
            ])
            enable_scheduled_query = True

        elif status == "ten_or_less":
            output_message = Message ([
                "✔️您查询的",from_station_name_input,"到",to_station_name_input,"，",range_time_message,"以下车次有票：\n",
                ticket,
            ])
        elif status == "over_ten":
            output_message = Message ([
                "⭐您查询的",from_station_name_input,"到",to_station_name_input,"，",range_time_message,"车票十分充足！以下仅显示部分车次：\n",
                ticket,
            ])

        user_id = event.get_user_id()

        
        if enable_scheduled_query == True:
            session_key = event.get_session_id()
            group_id = event.group_id if hasattr(event, "group_id") else None

            user_sessions[session_key] = { # 需查询的信息
                'from_station_name_input': from_station_name_input,
                'to_station_name_input': to_station_name_input,
                'from_station_telecode': from_station_telecode,
                'to_station_telecode': to_station_telecode,
                'train_date': train_date,
                'range_start_time_raw': range_start_time_raw,
                'range_end_time_raw': range_end_time_raw,
                'range_start_time': range_start_time,
                'range_end_time': range_end_time,
                'scheduled_query_time_raw': scheduled_query_time_raw,
                'scheduled_query_unit': scheduled_query_unit
            }

            # 初始化
            user_counts[session_key] = 0

            # 添加循环任务
            scheduler.add_job(
                query_reflection,
                "interval",
                minutes = scheduled_query_time,
                args = [bot, user_id, group_id,session_key],
                id = f"query_timer_{session_key}",
                replace_existing = True
            )


        await scheduled_query.finish(MessageSegment.at(user_id) + "\n" + output_message)

    else:

        await scheduled_query.finish(none_input_alert)

async def query_reflection(bot: Bot, user_id: int, group_id: int | None, session_key: str):
    """
    定时查询执行模块
    """
    # 计数+1
    user_counts[session_key] = user_counts.get(session_key, 0) + 1
    count = user_counts[session_key]

    session = user_sessions[session_key]
    from_station_name_input = session['from_station_name_input']
    to_station_name_input = session['to_station_name_input']
    from_station_telecode = session['from_station_telecode']
    to_station_telecode = session['to_station_telecode']
    train_date = session['train_date']
    range_start_time_raw = session['range_start_time_raw']
    range_end_time_raw = session['range_end_time_raw']
    range_start_time = session['range_start_time']
    range_end_time = session['range_end_time']
    scheduled_query_time_raw = session['scheduled_query_time_raw']
    scheduled_query_unit = session['scheduled_query_unit']

    response_data = await get_12306_remaining_tickets(train_date, from_station_telecode, to_station_telecode) # 因为上面已经进行过错误处理，如果上面有错误，在上面就已经被直接拦下了
    current_remaining_data = response_data['data']['result']

    filtered_remaining_data = time_filter(current_remaining_data, range_start_time, range_end_time)

    enable_scheduled_query = False
    ticket, status = await generate_output(filtered_remaining_data, train_date)
    range_time_message = time_range_output(range_start_time_raw, range_end_time_raw)
    if status == "no_tickets":
        scheduled_query_result = Message ([
            "❌抱歉，您查询的",from_station_name_input,"到",to_station_name_input,"，",range_time_message,"暂时无票\n",
        ])
        enable_scheduled_query = True

    elif status == "ten_or_less":
        scheduled_query_result = Message ([
            "✔️您查询的",from_station_name_input,"到",to_station_name_input,"，",range_time_message,"以下车次有票：\n",
            ticket,
        ])

    elif status == "over_ten":
        scheduled_query_result = Message ([
            "⭐您查询的",from_station_name_input,"到",to_station_name_input,"，",range_time_message,"车票十分充足！以下仅显示部分车次：\n",
            ticket,
        ])

    # 发送提醒
    output_message = scheduled_query_result + f"{scheduled_query_time_raw}{scheduled_query_unit}后将再次查询\n还将进行{str(10-count)}次查询"
    group_msg = f"[CQ:at,qq={user_id}]\n{output_message}"
    if group_id:
        await bot.send_group_msg(group_id=group_id, message=group_msg)
    else:
        await bot.send_private_msg(user_id=user_id, message=output_message)
    
    if enable_scheduled_query == False:
        cleanup_session(session_key)
    
    # 满10次，停止任务
    if count >= 9:
        cleanup_session(session_key)
        
        # 发送结束通知
        end_msg = f"{scheduled_query_result}最后一次定时查询完成！"
        if group_id:
            await bot.send_group_msg(group_id=group_id, message=f"[CQ:at,qq={user_id}]\n{end_msg}")
        else:
            await bot.send_private_msg(user_id=user_id, message=end_msg)

@cancel_scheduled_query.handle()
async def handle_cancel_scheduled_query(bot: Bot, event: MessageEvent):
    """
    用户主动取消定时查询
    """

    user_id = event.get_user_id()
    session_key = event.get_session_id()
    job_id = f"query_timer_{session_key}"

    if not scheduler.get_job(job_id):
        await cancel_scheduled_query.finish("你并没有正在进行的定时查询任务，无法取消")
    else:
        cleanup_session(session_key)
        await cancel_scheduled_query.finish("已取消定时查询任务")