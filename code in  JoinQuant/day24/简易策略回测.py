# 导入函数库
from jqdata import *
import pandas as pd
from jqlib.technical_analysis import *

# 初始化函数，设定基准等等
def initialize(context):
    # 设定沪深300作为基准
    set_benchmark('000300.XSHG')
    # 开启动态复权模式(真实价格)
    set_option('use_real_price', True)
    g.security='000001.XSHE'
    # 过滤掉order系列API产生的比error级别低的log
    # log.set_level('order', 'error')
    
    ### 股票相关设定 ###
    # 股票类每笔交易时的手续费是：买入时佣金万分之三，卖出时佣金万分之三加千分之一印花税, 每笔交易佣金最低扣5块钱
    set_order_cost(OrderCost(close_tax=0.001, open_commission=0.0003, close_commission=0.0003, min_commission=5), type='stock')
    g.macd_yesterday=0

def handle_data(context, data):
    security=g.security
    #计算当日MACD指标值
    DIF,DEA,_MACD=MACD(security_list=security,check_date=context.current_dt,SHORT=6,LONG=12,MID=9)
    #计算现金
    cash=context.portfolio.cash
    #计算金叉和死叉
    if g.macd_yesterday<0 and _MACD[security] >0 and cash>0:
        order_value(security,cash)
    elif g.macd_yesterday>0 and _MACD[security] <0 and \
            context.portfolio.positions[security].closeable_amount >0:
        order_target(security,0)
    #更新macd
    g.macd_yesterday=_MACD[security]
## 开盘前运行函数     
def before_market_open(context):
    pass
    
## 开盘时运行函数
def market_open(context):
    pass
 
## 收盘后运行函数  
def after_market_close(context):
    pass
