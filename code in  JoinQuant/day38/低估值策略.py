from jqdata import *
"""
市净率小于1
负债比例低于市场平均值
企业的流动资产至少是流动负债的1.2倍
每月调一次仓
可加入止损(十天沪深300指数下跌10%清仓)
"""
# 初始化函数，设定基准等等
def initialize(context):
    
    # 设置自定义基准
    set_benchmark('000001.XSHE')
    
    # 开启动态复权模式
    set_option('use_real_price', True)
    # 设定股票池 - 沪深300指数成分股
    g.stock_pool = '000300.XSHG'
    #设定指数
    g.stockindex= '000300.XSHG'
    #设置开启避免未来数据模式
    set_option("avoid_future_data",True)
    # 开启动态复权模式(真实价格)
    set_option('use_real_price', True)
    #设置成交量比例
    set_option("order_volume_ratio",1)
     #卖出时佣金万分之三加千分之一的印花税
    set_order_cost(OrderCost(open_tax=0,close_tax=0.001,open_commission=0.0003,close_commission=0.0003,close_today_commission=0,min_commission=5),type='stock')
   #最大持仓数量
    g.stocknum = 10
    g.ma_short = 20         # 短周期均线
    g.rsi_period = 14       # RSI周期
    g.rsi_buy = 30          # RSI买入阈值（超卖）
    g.rsi_sell = 70         # RSI卖出阈值（超买）
    #自动设置调仓月份
    f=12
    g.Transfer_date =list(range(1,13,12 // f))
    ## 运行函数（reference_security为运行时间的参考标的；传入的标的只做种类区分，因此传入'000300.XSHG'或'510300.XSHG'是一样的）
      # 根据大盘止损
    run_daily(broader_stoploss, time= 'open',reference_security='000300.XSHG') 
    #交易
    run_monthly(trade, monthday=20, time= 'open',reference_security='000300.XSHG') 
#选股
def check_stocks(context):
    #获取沪深成分股
    security =get_index_stocks(g.stockindex)
    
    stocks =get_fundamentals(query(
                    valuation.code,
                    valuation.pb_ratio,
                    balance.total_assets,
                    balance.total_liability,
                    balance.total_current_assets,
                    balance.total_current_liability
                    ).filter(
                        valuation.code.in_(security),
                        valuation.pb_ratio < 1,#市净率小于1
                        #企业的流动资产至少是流动负债的1.2倍
                        balance.total_current_assets / balance.total_current_liability  >1.2
                        )
                    )
    
    #计算股票的负债比例
    stocks['debt_asset']=stocks['total_liability']/stocks['total_assets']
    #计算负债比例的市场均值
    median =stocks['debt_asset'].median()
    #筛选符合标准的股票列表
    codes =stocks[stocks['debt_asset']<median].code
    return list(codes)
    
#根据大盘止损，具体用法看bm_stoploss
def broader_stoploss(context):
    stoploss =bm_stoploss(kernel=2,n=3,threshold=0.1)
    if stoploss:
        if len(context.portfolio.positions)>0:
            for stock in list(context.portfolio.positions.keys()):
                order_target(stock,0)
                
#大盘止损函数
def bm_stoploss(kernel=2,n=10,threshold=0.03):
    """
    方法1：当大盘N日均线与昨日收盘价构成死叉，则为True
    方法2：当大盘N日内跌幅超过阈值，则为True
    """
    
    #方法1
    if kernel ==1:
        t=n+2
        hist =attribute_history('000300.XSHG ',t,'1d','close',df=False)
        temp1=sum(hist['close'][1:-1]/float(n))
        temp2=sum(hist['close'][0:-2]/float(n))
        close1=hist['close'][-1]
        close2=hist['close'][-2]
        if (close2>temp2)and(close1>temp1):
            return True
        else:
            return False
    
    #止损方法2
    elif kernel == 2:
        hist1 = attribute_history('000300.XSHG',n,'1d','close',df=False)
        if ((1-float(hist1['close'][-1] / hist1['close'][0])) > threshold):
            return True
        else:
            return False
# 交易函数（每月20号开盘执行）
def trade(context):
#获取当前月份
    months = context. current_dt.month
#若当前月为交易月
    if months in g. Transfer_date:
#获取股票池
        buylist = check_stocks(context)

#卖出逻辑
        if len(context.portfolio.positions) > 0:
             for stock in context.portfolio.positions.keys():
                if not stock in buylist:
                    order_target(stock,0)

#分配买入资金
        if len(context.portfolio.positions) < g.stocknum:
            num = g.stocknum - len(context.portfolio.positions)
            cash = context.portfolio.cash / num
        else :
            cash = 0
            
        #买入逻辑
        if len(buylist)>0:
            for stock in buylist:
                if not stock in context.portfolio.positions.keys():
                    order_value(stock,cash)
    else:
        return
## 开盘前运行函数     
def before_market_open(context):
    pass
    
## 开盘时运行函数
def market_open(context):
    pass
 
## 收盘后运行函数  
def after_market_close(context):
    pass