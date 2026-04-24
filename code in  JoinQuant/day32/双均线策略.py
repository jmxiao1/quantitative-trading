# 导入函数库
from jqdata import *
"""
双均线策略
金叉时买入，死叉时卖出
"""

# 初始化函数，设定基准等等
def initialize(context):
    g.security= '000333.XSHE (000333.XSHE (MDJT)'
    g.short_count=5
    g.long_count=10
    g.unit='1d'
    run_daily(market_open,time='every_bar')
    
def market_open(context):
    #获取5日均线
    short_ma =get_ma(g.security,g.short_count,g.unit)
    #获取10日均线
    long_ma=get_ma(g.security,g.long_count,g.unit)
    
    #金叉时买入
    if get_golden_signal(short_ma,long_ma):
        print(f"金叉买入，MA{g.short_count}={short_ma},MA{g.long_count}={long_ma}")
        order_target(g.security,1000)
    elif get_death_signal(short_ma,long_ma):
        print(f"卖出所有股票,MA{g.short_count}={short_ma},MA{g.long_count}={long_ma}")
        order_target(security,0)

#计算MA
def get_ma(security:str,count:int,unit:str)->list:
    #获取count+1的收盘价
    df =attribute_history(security,count+1,unit,['close'])
    #计算ma
    now_ma =df[1:count+1]['close'].rolling(count).mean()[-1]
    #计算上次ma
    pre_ma=df[:count]['close'].rolling(count).mean[-1]
    
    return [pre_ma,noww_ma]  
"""
判断是否金叉
金叉：true
"""
def get_golden_signal(short_ma=list,long_ma=list)->bool:
    return (short_ma[0]<long_ma[0] and short_ma[1]>=long_ma[1])
"""
判断是否死叉
死叉：true
"""
def get_death_signal(short_ma=list,long_ma=list)->bool:
    return (short_ma[0]>long_ma[0] and short_ma[1]<=long_ma[1])
## 开盘前运行函数     
def before_market_open(context):
    pass
    
## 开盘时运行函数
def market_open(context):
    pass
 
## 收盘后运行函数  
def after_market_close(context):
    pass
