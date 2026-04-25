# 导入函数库
from jqdata import *
import jqdata
from jqlib.technical_analysis import *
"""
KDJ量化交易策略
超买超卖型技术指标KDJ
实现K线在20左右向上交叉D线，买入
-K线在80左右向下交叉D线，卖出
"""
# 初始化函数，设定基准等等
def initialize(context):
    # 设定沪深300作为基准
    set_benchmark('000300.XSHG')
    # 开启动态复权模式(真实价格)
    set_option('use_real_price', True)
    #卖出时佣金万分之三加千分之一的印花税
    set_order_cost(OrderCost(open_tax=0,close_tax=0.001,open_commission=0.0003,close_commission=0.0003,close_today_commission=0,min_commission=5),type='stock')
    #开盘前运行
    run_daily(before_market_open, time='before_open',reference_security='000300.XSHG')
    ##开盘时运行
    run_daily(market_open,time='open',reference_security='000300.XSHG')
    #收盘后运行
    run_daily(after_market_close,time='after_close',reference_security='000300.XSHG')
## 开盘前运行函数     
def before_market_open(context):
    #输出运行时间
    log.info("""一天交易开始""")
    log.info(""" before_market_open运行时间：{}""".format(str(context.current_dt.time())))
    g.security='000001.XSHE'
    
## 开盘时运行函数
def market_open(context):
      #输出运行时间
    log.info("""market_open运行时间：{}""".format(str(context.current_dt.time())))
    security = g.security
    #调用KD函数，获取该股票的K和D值
    K1,D1,_=KDJ(security,check_date=context.current_dt,N=9,M1=3,M2=6)
    #获取现金
    cash=context.portfolio.available_cash
    #识别买入信号，K线在20左右向上交叉D线，买入
    if K1[security]>=20 and K1[security]>D1[security]:
        #买入日志
        log.info("""买入股票{}""".format(security))
        order_value(security,cash)
     #识别卖出信号，K线在80左右向下交叉D线，卖出
    if K1[security]<80 and K1[security]<D1[security] and context.portfolio.positions[security].total_amount > 0 :
         #卖出日志
        log.info("""卖出股票{}""".format(security))
        order_target(security,0)
 
## 收盘后运行函数  
def after_market_close(context):
    #收盘后运行函数
    #输出运行时间
    log.info("""after_market_close运行时间：{}""".format(str(context.current_dt.time())))
    #获得当天所有成交记录
    trades =get_trades()
    for _trade in trades.values():
        log.info("""成交记录：{}""".format(str(_trade)))
    
    log.info("""当天交易结束""")
