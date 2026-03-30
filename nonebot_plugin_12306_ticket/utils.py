import re
import datetime

class utils:
    normal_date_pattern = re.compile(r'\d{4}-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])')
    chinese_date_pattern = re.compile(r'\d{4}年([1-9]|1[0-2])月([1-9]|[12]\d|3[01])日')
    train_no_pattern = re.compile(r'[A-Za-z]\d{1,4}|\d{4}') 
    station_name_pattern = re.compile(r'^[\u4e00-\u9fff]+$')
    departure_time_range_pattern = re.compile(r'^(\d+)-(\d+)$')
    scheduled_query_pattern = re.compile(r'(\d+)\s*(小时|分钟)')

    today = datetime.date.today().strftime("%Y-%m-%d")
    tomorrow = (datetime.date.today() + datetime.timedelta(days=1)).strftime("%Y-%m-%d")
    # now_time = datetime.datetime.now().strftime("%Y-%m-%d-%H:%M")  