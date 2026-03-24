from nonebot import on_command
from nonebot.params import CommandArg, ArgPlainText  # type: ignore
from nonebot.adapters.onebot.v11 import MessageEvent, Bot, MessageSegment, Message
from nonebot import require
from typing import Optional
import datetime
from .get_data import get_12306_remaining_tickets,get_12306_price
from .telecode import get_telecode, get_station_name
from .utils import utils

require("nonebot_plugin_apscheduler")
from nonebot_plugin_apscheduler import scheduler # type: ignore

scheduled_query = on_command("定时查询", priority=5, block=True)

# 存储每个用户的计数
user_counts = {}  # {user_id: 当前第几次}

async def generate_output(current_remaining_data :str, train_date :str) -> Optional[str]:
    """
    查询余票并输出模块化
    """
    hr_line = "------------------------------\n"
    output = ""
    for data_count in range(len(current_remaining_data)):
        pass # TODO
# async def generate_output
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
                range_start_time = datetime.datetime.strftime(f'{int(range_start_time_raw):02}:00', '%H:%M')
                range_end_time = datetime.datetime.strptime(f'{int(range_end_time_raw):02}:00', '%H:%M')
            elif scheduled_query_match:
                scheduled_query_time = scheduled_query_match.group(1)
                scheduled_query_unit = scheduled_query_match.group(2) # 捕获单位（小时、分钟）
                if scheduled_query_unit == "小时":
                    scheduled_query_time = int(scheduled_query_time) *60 # 转化为分钟

        if train_date == "" or train_date < utils.today:
            train_date = utils.today 
        # 获取并格式化用户输入结束
    
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
        
        #  TODO 余票数量判断
        

        user_id = event.user_id
        group_id = event.group_id if hasattr(event, "group_id") else None
        
        # 初始化计数器
        user_counts[user_id] = 0
        
        # 添加循环任务
        scheduler.add_job(
            query_reflection,
            "interval",
            minutes=scheduled_query_time,
            args=[bot, user_id, group_id],
            id=f"query_timer_{user_id}",
            replace_existing=True  # 如果已有任务，替换掉
        )
        
        await scheduled_query.send("⏱️ 计时开始，每隔1小时提醒，共5次")
    else:

        await scheduled_query.finish(none_input_alert)

async def query_reflection(bot: Bot, user_id: int, group_id: int | None):
    # 计数+1
    user_counts[user_id] = user_counts.get(user_id, 0) + 1
    count = user_counts[user_id]
    
    # 发送提醒
    msg = f"[CQ:at,qq={user_id}] ⏰ 第{count}小时提醒！"
    if group_id:
        await bot.send_group_msg(group_id=group_id, message=msg)
    else:
        await bot.send_private_msg(user_id=user_id, message=f"⏰ 第{count}小时提醒！")
    
    # 满5次，停止任务
    if count >= 5:
        scheduler.remove_job(f"query_timer_{user_id}")
        del user_counts[user_id]
        
        # 发送结束通知
        end_msg = "✅ 5组计时全部完成！"
        if group_id:
            await bot.send_group_msg(group_id=group_id, message=f"[CQ:at,qq={user_id}] {end_msg}")
        else:
            await bot.send_private_msg(user_id=user_id, message=end_msg)