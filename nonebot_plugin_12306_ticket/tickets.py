import httpx
# import json
import urllib3
import re
import datetime
from nonebot import on_command   # type: ignore
from nonebot.adapters.onebot.v11 import Message, MessageSegment   # type: ignore
from nonebot.plugin import PluginMetadata  # type: ignore
from nonebot.params import CommandArg  # type: ignore
from nonebot.rule import to_me  # type: ignore
# from .utils import utils
from .api import API

tickets_info = on_command("车票", aliases={"cp","ticket","tickets"}, priority=5, block=True)

@tickets_info.handle()
async def handle_tickets_info(args: Message = CommandArg()):
    if user_input := args.extract_plain_text():

        # 对用户的输入数据进行处理
        user_input_separate = user_input.split(" ") # 用空格分开各个参数
        input_separate_checker = len(user_input_separate)
        if input_separate_checker > 4 or input_separate_checker < 2:
            await tickets_info.finish("格式错误，请输入车次（可选） 出发站 到达站 日期（可选）")
        else:
            normal_date_pattern = re.compile(r'\d{4}-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])') # 匹配 YYYY-MM-DD
            chinese_date_pattern = re.compile(r'\d{4}年([1-9]|1[0-2])月([1-9]|[12]\d|3[01])日') # 匹配 YYYY年M月D日
            train_no_pattern = re.compile(r'[A-Za-z]\d{1,4}|\d{4}') 
            station_name_pattern = re.compile(r'^[\u4e00-\u9fff]+$') # 仅识别全中文
            today = datetime.date.today().strftime("%Y-%m-%d") # YYYY-MM-DD
            tomorrow = (datetime.date.today() + datetime.timedelta(days=1)).strftime("%Y-%m-%d")

            train_date = ""
            train_no = ""
            from_station_name = ""
            # to_station_name = ""
            for i in range(input_separate_checker):
                current_arg = user_input_separate[i]
                # date_matches = date_pattern.search(current_arg)
                normal_date_match = normal_date_pattern.search(current_arg)
                chinese_date_match = chinese_date_pattern.search(current_arg)
                train_no_match = train_no_pattern.findall(current_arg)
                if normal_date_match or chinese_date_match or "今天" in current_arg or "明天" in current_arg: # 提取时间
                    if "今天" in current_arg:
                        train_date = today
                    elif "明天" in current_arg:
                        train_date = tomorrow
                    else:
                        if normal_date_match:
                            year = normal_date_match.group(0)[:4]
                            month = normal_date_match.group(1)
                            day = normal_date_match.group(2)
                        elif chinese_date_match:  # 中文格式 YYYY年M月D日
                            year = chinese_date_match.group(0)[:4]
                            month = chinese_date_match.group(1)
                            day = chinese_date_match.group(2)
                        # 统一格式化为 XXXX-XX-XX
                        train_date = f"{year}-{month.zfill(2)}-{day.zfill(2)}"

                elif train_no_match: # 提取车次
                    train_no = current_arg.upper() # TODO:看看这个0去掉可不可以

                elif station_name_pattern.match(current_arg):
                    if from_station_name == "":
                        from_station_name = current_arg
                    else:
                        to_station_name = current_arg
            
            if train_date == "" or train_date < today:
                train_date = today
        
        await tickets_info.finish(f"车次：{train_no}，发站：{from_station_name}，到站：{to_station_name}，时间：{train_date}")



    else:
        await tickets_info.finish("请输入车次（可选） 出发站 到达站 日期（可选）")
