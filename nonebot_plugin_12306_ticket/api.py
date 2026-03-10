class API:
    telecode_url = "https://kyfw.12306.cn/otn/resources/js/framework/station_name.js" # 获取电报码
    init_url = "https://kyfw.12306.cn/otn/leftTicket/init" # 获取cookie
    # ticket_query_url = "https://kyfw.12306.cn/otn/leftTicket/query" # 票务系统
    ticket_query_url = "https://kyfw.12306.cn/otn/"
    ticket_price_url = "https://kyfw.12306.cn/otn/leftTicket/queryTicketPrice"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Referer": "https://kyfw.12306.cn/otn/leftTicket/init",
        "Accept": "application/json, text/plain, */*",
        "Host": "kyfw.12306.cn"
    }    