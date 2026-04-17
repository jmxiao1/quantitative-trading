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
    g.macd_yesterday=0
        # 设置手续费和滑点
    set_order_cost(OrderCost(close_tax=0.001, open_commission=0.0003, 
                            close_commission=0.0003, min_commission=5), 
                   type='stock')
    set_slippage(FixedSlippage(0.002))


#进行操作过程
def handle_data(context, data):
    security = g.security
    #计算当天macd值
    DIF,DEA,_MACD=MACD(security_list=security,check_date=context.current_dt,SHORT=6,LONG=12,MID=9)
    #获取当日现金
    cash=context.portfolio.cash
    #如果昨日的macd为负，今日macd为正，则表示为金叉
    if g.macd_yesterday < 0 and _MACD[security] > 0 and cash > 0:
        order_value(security,cash)
        log.info('金叉买入: %s, 买入金额: %.2f' % (security, cash * 0.99))
    elif g.macd_yesterday>0 and _MACD[security] < 0 and \
         context.portfolio.positions[security].closeable_amount>0:
        order_target(security,0)
        log.info('死叉卖出: %s' % security)
        
    g.macd_yesterday = _MACD[security]
## 开盘前运行函数     

def before_market_open(context):
    pass
    
## 开盘时运行函数
def market_open(context):
    pass
 
## 收盘后运行函数  
def after_market_close(context):
     # 记录每日持仓情况
    log.info('收盘持仓: %s' % context.portfolio.positions)
    
    # 可以在这里发送邮件通知或保存数据
    # send_message('策略运行完成')
    
    # 打印收益率信息
    returns = context.portfolio.returns
    log.info('累计收益率: %.2f%%' % (returns * 100))
