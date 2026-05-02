#大小盘轮动量化交易策略
#导入函数库
from jqdata import *
from datetime import datetime, timedelta  # 添加 timedelta
import math
import pandas as pd
import statsmodels.api as sm
import numpy as np

#设定基础参数
strBig = '000300.XSHG'
strSmall = '399006.XSHE'
strMarket = '000047.XSHG'
index = [strBig, strSmall, strMarket]
etfBig = '510300.XSHG'
etfSmall = '159915.XSHE'
g.result = {etfBig: 0, etfSmall: 0}

def initialize(context):
    # 设置自定义基准
    set_benchmark('000001.XSHE')
    # 开启动态复权模式
    set_option('use_real_price', True)
    #设置开启避免未来数据模式
    set_option("avoid_future_data", True)
    # 开启动态复权模式(真实价格)
    set_option('use_real_price', True)
    #设置成交量比例
    set_option("order_volume_ratio", 1)
    #卖出时佣金万分之三加千分之一的印花税
    set_order_cost(OrderCost(open_tax=0, close_tax=0.001, open_commission=0.0003, 
                             close_commission=0.0003, close_today_commission=0, 
                             min_commission=5), type='stock')
    run_monthly(market_open,monthday=1)

#计算交易信号
def get_signal(tradeDate):
    start_date = datetime.strptime(tradeDate, '%Y-%m-%d') - timedelta(days=1000)
    start_date = start_date.strftime('%Y-%m-%d')
    #获取数据
    data = get_price(index, start_date=start_date, end_date=tradeDate, 
                     frequency='daily', fields='close', fq='pre')['close']
    data = data / data.shift(250)
    data.dropna(inplace=True)
    
    #计算RS指标
    for c in data.columns:
        if c != strMarket:
            data[c] = data[c] - data[strMarket] + 1
    data = data.drop(strMarket, axis=1)  # 添加 axis=1
    for c in data.columns:
        data[c] = data[c].apply(lambda x: math.log(x, 10))
    
    #计算RS的HP滤波
    diff = data[strBig] - data[strSmall]  # 修正拼写错误
    cycle, trend = sm.tsa.filters.hpfilter(diff, lamb=10000)  # 修正为 sm.tsa
    
    #计算前20个数据一阶及二阶导数
    t1 = []
    for pos in range(-20, 0):
        X = list(np.arange(20))
        X = sm.add_constant(X)  # 修正：x 改为 X
        est = sm.OLS(trend.iloc[pos - 20:pos], X)  # 修正：x 改为 X
        est = est.fit()
        t1.append(est.params['x1'])
    
    X = list(np.arange(20))
    X = sm.add_constant(X)  # 修正：x 改为 X
    est1 = sm.OLS(t1, X)  # 修正：x 改为 X
    est1 = est1.fit()
    t2 = est1.params[1]  # 二阶导数
    result = {}
    
    #通过四象限结果计算持仓比例
    if t1[-1] > 0 and t2 > 0:
        result[etfBig] = 1
        result[etfSmall] = 0
    elif t1[-1] > 0 and t2 < 0:  # 使用 elif
        result[etfBig] = 0.5
        result[etfSmall] = 0.5
    elif t1[-1] < 0 and t2 > 0:  # 使用 elif
        result[etfBig] = 0.5
        result[etfSmall] = 0.5
    elif t1[-1] < 0 and t2 < 0:  # 使用 elif
        result[etfBig] = 0
        result[etfSmall] = 1
    
    return result

#交易函数,开盘时运行
def market_open(context):
    result = get_signal(context.previous_date.strftime('%Y-%m-%d'))  # 修正日期格式
    #若当前持仓与计算出的持仓比例不一致,交易调仓
    if not (g.result[etfBig] == result[etfBig] and g.result[etfSmall] == result[etfSmall]):
        #先清仓
        order_target_value(etfBig, 0)
        order_target_value(etfSmall, 0)  # 修正拼写错误
        
        #根据现金买入指定比例etf
        cash = context.portfolio.available_cash
        order_target_value(etfBig, result[etfBig] * cash)
        order_target_value(etfSmall, result[etfSmall] * cash)
        
        g.result = result