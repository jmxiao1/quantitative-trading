# 导入聚宽函数库
from jqdata import *
import talib
from jqlib.technical_analysis import *
import numpy as np
import pandas as pd

# 初始化函数，设定基准等等
def initialize(context):
    g.security ='000001.XSHE' 
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
   
    
      # 开盘前运行
    run_daily(before_market_open, time='before_open', reference_security='000300.XSHG') 
      # 开盘时或每分钟开始时运行
    run_daily(market_open, time='every_bar', reference_security='000300.XSHG')
      # 收盘后运行
    run_daily(after_market_close, time='after_close', reference_security='000300.XSHG')

def handle_data(context, data):
    #计算能量型指标
    security=g.security
    #计算BR,AR
    BR1,AR1=BRAR(security,check_date=context.current_dt,N=26)
    #计算中间意愿CR
    CR1,MA1,MA2,MA3,MA4=CR(security,check_date=context.current_dt,N=26,M1=10,M2=20,M3=40,M4=60)
    #计算成交量变异率VR
    VR1,MAVR1= VR(security,check_date=context.current_dt,N=26,M=6)
    #计算现金
    cash=context.portfolio.cash
    
    #识别买入信号
    #当AR<100,BR<100,BR<AR, CR<100, VR<100时，买入股票
    if AR1[security]<100 and BR1[security]<100 and CR1[security]<100 and VR1[security]<100 and BR1[security]<AR1[security]:
        order_value(security,cash)
        log.info("买入股票%s"%(security))
        
    #识别卖出信号
    #当AR>150,BR>150,BR>AR, CR>150, VR>150时，卖出股票
    elif AR1[security]>150 and BR1[security]>150 and CR1[security]>150 and VR1[security]>150 :
        order_target(security,0)
        log.info("卖出股票%s"%(security))

## 开盘前运行函数  
def before_market_open(context):
    pass
    
## 开盘时运行函数
def market_open(context):
    pass
 
## 收盘后运行函数  
def after_market_close(context):
    pass
