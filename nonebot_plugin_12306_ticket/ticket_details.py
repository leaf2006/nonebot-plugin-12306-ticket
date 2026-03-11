from .telecode import get_station_name
import asyncio
# #     return avaliable_dict
def format_data(ticket_remaining_data,ticket_price):
    """
    将余票数据与票价数据整合成一个dict
    """
    seat_code_to_chinese = {
        'O': '二等座',
        'M': '一等座',
        'A9': '商务座', 
        'F': '动卧',
        'A1': '硬座',
        'A2': '软座', 
        'A3': '硬卧',
        'A4': '软卧',
        'A5': '高级软卧',
        'WZ': '无座'
    }

    result_dict = {}

    seat_code_avaliable = ticket_price['data']
    # except_data = seat_code_avaliable['OT']
    
    # 按照 seat_code_to_chinese 的顺序遍历，确保输出顺序一致
    for seat_code, chinese_name in seat_code_to_chinese.items():
        if seat_code in seat_code_avaliable and not isinstance(seat_code_avaliable[seat_code], list):
            result_dict[chinese_name] = seat_code_avaliable[seat_code]

    split_remaining_data = ticket_remaining_data.split('|')

    remaining_ticket = {
        "二等座": split_remaining_data[30],
        "一等座": split_remaining_data[31],
        "商务座": split_remaining_data[32],
        "动卧": split_remaining_data[33],
        "硬座": split_remaining_data[29],
        "软座": split_remaining_data[23],
        "硬卧": split_remaining_data[28],
        "软卧": split_remaining_data[23],
        "高级软卧": split_remaining_data[21],
        "无座": split_remaining_data[26]   
    }

    for seat_name, remain in remaining_ticket.items():
        if seat_name in result_dict:
            if remain == "有" or remain == "无":
                result_dict[seat_name] = f"{result_dict[seat_name]} {remain}"
            else:
                result_dict[seat_name] = f"{result_dict[seat_name]} {remain}张"

    return result_dict

async def get_basic_info(ticket_remaining_data):
    p = ticket_remaining_data.split('|')

    train_no = p[3]
    departure_station_name, terminal_station_name = await get_station_name(p[4], p[5]) # 始发站，终到站
    from_station_name, to_station_name = await get_station_name(p[6], p[7]) # 出发站，到达站
    start_time = p[8] # 出发时
    end_time = p[9] # 到达时
    duration = p[10] # 耗时

    return train_no,departure_station_name,terminal_station_name,from_station_name,to_station_name,start_time,end_time,duration # 怎么那么长，不笑都不行
