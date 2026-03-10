def parse_train_data(data_string):
    p = data_string.split('|')
    
    # train_result = {
    #     "train_no": p[3],          # 车次
    #     "train_unique_id": p[2],   # 车次唯一编号     
    #     "start_time": p[8],        # 出发时间
    #     "from_station_no": p[16],   # 出发站序号
    #     "to_station_no": p[17],    # 到达站序号 
    #     "end_time": p[9],          # 到达时间
    #     "duration": p[10],         # 历时
    #     "date": p[13],             # 日期
    #     "seat_types": p[34],       # 席位字典
    #     "tickets": {
    #         "二等座": p[30] if p[30] else "--",
    #         "一等座": p[31] if p[31] else "--",
    #         "商务座": p[32] if p[32] else "--",
    #         "动卧": p[33] if p[33] else "--",
    #         "硬座": p[29] if p[29] else "--",
    #         "软座": p[23] if p[23] else "--",
    #         "硬卧": p[28] if p[28] else "--",
    #         "软卧": p[23] if p[23] else "--",
    #         "高级软卧": p[21] if p[21] else "--",
    #         "无座": p[26] if p[26] else "--"
    #     }
    # }
    train_result = {
        "train_no": p[3],          # 车次
        "train_unique_id": p[2],   # 车次唯一编号     
        "start_time": p[8],        # 出发时间
        "from_station_no": p[16],   # 出发站序号
        "to_station_no": p[17],    # 到达站序号 
        "end_time": p[9],          # 到达时间
        "duration": p[10],         # 历时
        "date": p[13],             # 日期
        "seat_types": p[34],       # 席位字典
        "tickets": {
            "O": p[30] if p[30] else "--", # 二等座
            "M": p[31] if p[31] else "--", # 一等座
            "A9": p[32] if p[32] else "--", # 商务座
            "F": p[33] if p[33] else "--", # 动卧
            "A1": p[29] if p[29] else "--", # 硬座
            "A2": p[23] if p[23] else "--", # 软座
            "A3": p[28] if p[28] else "--", # 硬卧
            "A4": p[23] if p[23] else "--", # 软卧
            "A6": p[21] if p[21] else "--", # 高级软卧
            "WZ": p[26] if p[26] else "--" # 无座
        }
    }
    return train_result

# def format_pricesystem(seat_code_raw):

#     seat_code_to_chinese = {
#         'O': '二等座',
#         'M': '一等座',
#         'A9': '商务座', 
#         'F': '动卧',
#         'A1': '硬座',
#         'A2': '软座', 
#         'A3': '硬卧',
#         'A4': '软卧',
#         'A5': '高级软卧',
#         'WZ': '无座'
#     }

#     avaliable_dict = {}
#     # except_dict = {}
#     seat_code_avaliable = seat_code_raw['data']
#     # except_data = seat_code_avaliable['OT']
    
#     # 按照 seat_code_to_chinese 的顺序遍历，确保输出顺序一致
#     for seat_code, chinese_name in seat_code_to_chinese.items():
#         if seat_code in seat_code_avaliable and not isinstance(seat_code_avaliable[seat_code], list):
#             avaliable_dict[chinese_name] = seat_code_avaliable[seat_code]

        
    
#     return avaliable_dict

def format_data(ticket_remaining_data,ticket_price):

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