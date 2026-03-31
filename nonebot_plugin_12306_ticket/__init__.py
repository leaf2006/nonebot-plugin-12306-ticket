from nonebot import get_plugin_config
from nonebot.plugin import PluginMetadata
from .tickets import handle_tickets_info
from .scheduled_query import handle_timer

# 插件配置页
__plugin_meta__ = PluginMetadata(
    name="12306车票查询",
    description="12306车票查询机器人，助你漫漫回家路",
    usage="""
    /车票 [出发站] [到达站] [日期（选填）] - 查询从出发站至到达站间的列车票价及余票数量
    /定时查询 [出发站] [到达站] [日期（选填）] [列车出发时间范围（可选）] [持续查询时间价格（分钟/小时）] - 定时查询车票情况
    /取消查询 - 取消定时查询任务
    """,

    type="application",
    # 发布必填，当前有效类型有：`library`（为其他插件编写提供功能），`application`（向机器人用户提供功能）。

    homepage="https://github.com/leaf2006/nonebot-plugin-12306-ticket",
    # 发布必填。

    supported_adapters={"~onebot.v11"},
    # 支持的适配器集合，其中 `~` 在此处代表前缀 `nonebot.adapters.`，其余适配器亦按此格式填写。
    # 若插件可以保证兼容所有适配器（即仅使用基本适配器功能）可不填写，否则应该列出插件支持的适配器。
)