# 导入聚宽函数库
from jqdata import *
import talib
from jqlib.technical_analysis import *
import numpy as np
import pandas as pd

# 初始化函数，设定基准等等
def initialize(context):
    # 设定沪深300作为基准
    set_benchmark('000300.XSHG')
    # 开启动态复权模式
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
      # 选股
    run_weekly(check_stocks, weekday=1, time= 'before_open',reference_security='000300.XSHG') 
    #交易
    run_weekly(trades, weekday=1, time= 'open',reference_security='000300.XSHG') 

#选股函数
def check_stocks(context):
    g.stocks =get_index_stocks('399808.XSHE')
    #查询股票市净率，并按照升序排序
    if len(g.stocks)>=0:
        g.df =get_fundamentals(
            query(
                valuation.code,valuation.pb_ratio
                ).filter(
                        valuation.code.in_(g.stocks
                        )
                ).order_by(
                            valuation.pb_ratio.asc()
                    )
                )
        g.code=g.df['code'][0]
#交易函数
def trades(context):
    if len(g.stocks)>0:
        code=g.code
        #看持仓股票不是最低市净率的股票，卖出
    for stock in context.portfolio.positions.keys():
        if stock != code:
            order_target=(stock,0)
    #持仓股票
    if len(context.portfolio.positions) >0:
            return
    else:
        order_value(code,context.portfolio.cash)
        
