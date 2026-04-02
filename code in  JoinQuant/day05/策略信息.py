# 导入函数库
from jqdata import *

# 初始化函数，设定基准等等
def initialize(context):
    # 设定沪深300作为基准
    set_benchmark('000300.XSHG')
    g.security ='000001.XSHE'
    ##run_weekly(market_open,1,time='open')
    run_daily(after_market_close,time='15:30')

def handle_data(context, data):
    ##context.portfolio变为整数1
    #context.portfolio = 1
    #lgo.info(context.portfolio.total_value)

    
    #总资产
    log.info(context.portfolio.total_value)
    #持仓余额
    log.info(context.portfolio.positions_value)
    #今日日期
    log.info(context.current_dt.day)
    #总权益的累计收益
    log.info(context.portfolio.returns)
    #获取仓位subportfolios[0]的可用资金
    log.info(context.subportfolios[0].available_cash)
    
    
