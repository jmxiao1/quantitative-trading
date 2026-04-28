# 导入聚宽函数库
from jqdata import *
import talib
from jqlib.technical_analysis import *
import numpy as np
import pandas as pd

def initialize(context):
    """
    初始化函数：设置策略基本参数
    """
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
    #持仓天数
    g.hold_cnt=0
    g.stock_num=10
    # 运行函数
    run_daily(trade, time='14:50',reference_security='000300.XSHG') # 开盘时运行

def check_stocks(context):
    """
    开盘执行函数：遍历股票池并执行买卖逻辑
    """
    now =context.current_dt
    g.buylist=[]
    # 获取目标股票
    security_list=get_all_stock(context,now,200)
    #获取股价
    h =get_bars(security_list,count=1,unit='1d',end_dt=now,fields=['close'],include_now=True)
    #获取MA200
    MA200=MA(security_list,check_date=now,timeperiod=200,unit='1d',include_now=True)
    #获取RSI10
    RSI10=RSI(security_list,check_date=now,N1=10)
    
   # 按条件选股
    for security in security_list:
        # 收盘价高于MA200
        MA_True = h[security]['close'] > MA200[security]
        # RSI10小于25
        RSI_True = RSI10[security] < 25
        # 获取股票池
        if MA_True and RSI_True:
            g.buylist.append(security)
        if len(g.buylist) == g.stock_num:
            break
    
    log.info('今日买入股票池：' + str(g.buylist))
    return g.buylist
# 获取目标股票，过滤st、科创板、创业板、退市、次新股
def get_all_stock(context, now, ndays):
    df = get_all_securities(types=['stock'],date=now)
    df = df[(~df['display_name'].str.contains("ST")) & 
    (~df['display_name'].str.contains("退")) & 
    (~df['display_name'].str.contains("\*")) & 
    ((df.index.str[0:3] != '300') & 
    (df.index.str[0:3] != '688'))]
    
    # 判断上市天数是否满足要求
    return [str(stock) for stock in df.index if (now.date() - df.loc[stock, 'start_date']).days > ndays]
 
#交易 
def trade(context):
    log.info('天数: ' + str(g.hold_cnt))
    # 获取当天时间
    now = context.current_dt
    # 获取持仓股票
    holding_list = list(context.portfolio.positions.keys())
    # 获取持仓股票现价
    h = get_bars(holding_list, count=1, unit='1d', end_dt=now, fields=['close'], include_now=True)
    # 根据策略交易

    # 没有持仓，买入目标股票
    if len(holding_list) == 0:
        buy_list = check_stocks(context)
        for security in buy_list:
            cash = context.portfolio.cash / len(buy_list)
            order_value(security, cash)  # 修正：order_value(security, cash)
            g.hold_cnt += 1
            log.info('买入股票: ' + str(security))
    # 根据卖出策略卖出（持仓超过11天；RSI > 40；下跌超过-5%）
    elif g.hold_cnt > 0 and g.hold_cnt < 11:
        g.hold_cnt += 1
        for security in holding_list:
            RSI10 = RSI(security, check_date=now, N1=10)  # 需要定义参数
            current_price = h[security]['close']
            cost = context.portfolio.positions[security].avg_cost  # 获取持仓成本价
            # 卖出条件判断
            if current_price < 0.95*cost or RSI10[security] > 40:
                order_target_value(security, 0)  # 清仓卖出
                log.info('卖出股票: ' + str(security))
            
    #持仓时间到达11天，卖出持仓股票
    elif g.hold_cnt >= 11:  # 持仓超过11天，全部卖出
        buy_list =check_stocks(context)
        for security in holding_list:
            order_target_value(security, 0)
            log.info('卖出股票(超期): ' + str(security))
            g.hold_cnt = 0
        for security in buy_list:
            cash = context.portfolio.cash / len(buy_list)
            order_value(security, cash)  # 修正：order_value(security, cash)
            g.hold_cnt += 1
            log.info('买入股票: ' + str(security))
            
    else:
        log.info("交易出错")