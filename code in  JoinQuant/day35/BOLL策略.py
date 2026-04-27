# 导入聚宽函数库
from jqdata import *
import talib
from jqlib.technical_analysis import *
import numpy as np
import pandas as pd

# 初始化函数，设定基准等等
def initialize(context):
    g.security ='002389.XSHE' 
    #设置N值
    g.k=2
    # 设定沪深300作为基准
    set_benchmark('000300.XSHG')
    # 开启动态复权模式(真实价格)
    set_option('use_real_price', True)
    # 设定股票池 - 沪深300指数成分股
    g.stock_pool = '000300.XSHG'
    # 设置基准
    set_benchmark('000300.XSHG')
    #设置开启避免未来数据模式
    set_option("avoid_future_data",True)
    # 开启动态复权模式(真实价格)
    set_option('use_real_price', True)
    #设置成交量比例
    set_option("order_volume_ratio",1)
     #卖出时佣金万分之三加千分之一的印花税
    set_order_cost(OrderCost(open_tax=0,close_tax=0.001,open_commission=0.0003,close_commission=0.0003,close_today_commission=0,min_commission=5),type='stock')
   
    ## 运行函数（reference_security为运行时间的参考标的；传入的标的只做种类区分，因此传入'000300.XSHG'或'510300.XSHG'是一样的）
      # 开盘前运行
    run_daily(before_market_open, time='before_open', reference_security='000300.XSHG') 
      # 开盘时或每分钟开始时运行
    run_daily(market_open, time='every_bar', reference_security='000300.XSHG')
      # 收盘后运行
    run_daily(after_market_close, time='after_close', reference_security='000300.XSHG')

#盘中的BOLL量化交易策略
def handle_data(context, data):
    #获取20日收盘价
    sr =attribute_history(g.security, 20)['close']
    #获取20日均价
    ma =sr.mean()
    #计算up线(压力线)，20日均线+N*SD(SD为20日收盘价标准差)
    up =ma+g.k*sr.std()
     #计算down线(支撑线)，20日均线-N*SD(SD为20日收盘价标准差)
    down =ma-g.k*sr.std()
    
    #获取股票开盘价
    p =get_current_data()[g.security].day_open
    #获取现金
    cash=context.portfolio.available_cash
    #持仓信息
    #买入信号，跌破支撑线
    if p<down and g.security not in context.portfolio.positions:
        order_value(g.security,cash)
    elif p>up and g.security in context.portfolio.positions:
        order_target(g.security,0)
        
    #卖出信号，突破压力线
## 开盘前运行函数     
def before_market_open(context):
    pass
    
## 开盘时运行函数
def market_open(context):
    pass
 
## 收盘后运行函数  
def after_market_close(context):
    pass
