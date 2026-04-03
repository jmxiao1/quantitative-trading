# 导入函数库
from jqdata import *
import datetime
from datetime import timedelta
#白马股选股
#一，筛选条件：
#    1.总市值>50亿（市值较大的公司，流动性好，竞争力强）
#    2.上市天数>750（抛开3年以内的次新
#    3.流通盘比例>95%（要全流通壁面解禁压力）
#    4.销售毛利率>20%（毛利率要高）
#    5.扣非净资产收益率>20%(ROE要高)
#二，排名条件：
#    1.总市值从大到小排列
# 初始化函数，设定基准等等
def initialize(context):
    #设定沪深300为基准
    set_benchmark('000300.XSHG')
    #开启动态复权模式
    set_option('use_real_price',True)
    #设定成交量比例
    set_option('order_volume_ratio',1)
    #设定股票交易手续费
    set_order_cost(OrderCost(open_tax=0,close_tax=0.001,open_commission=0.003,
                    close_commission =0.003,close_today_commission=0,
                    min_commission=5),type='stock')
    #设定持仓数量
    g.stocknum =20
    #交易日计时器
    g.days=20
    #调仓频率
    g.refresh_rate =100
    #运行函数
    run_daily(trade,'every_bar')

#排除次数
def delete_stock(stocks,beginDate,n=180):
    #去除上市距beginDate不足n天的股票
    stockList=[]
    for stock in stocks:
        start_date =get_security_info(stock).start_date
        if start_date<(beginDate - timedelta(days =n)).date():
            stockList.append(stock)
    return stockList
#筛选逻辑
def check_stocks(context):
    #设定查询条件
    q =query(
        indicator.code,
        valuation.capitalization,indicator.roe,
        indicator.gross_profit_margin,).filter(
            #1，总市值大于50亿
            valuation.capitalization >50,
            #3，流通盘比例>95%
            valuation.circulating_market_cap / valuation.market_cap > 0.95,
            #4.销售毛利率>20%
            indicator.gross_profit_margin>20,
            #5，扣非净资产收益率>20%
            indicator.roe>20,).order_by(
                #按市值倒序排序
                valuation.market_cap.desc()
                ).limit(100)
    df =get_fundamentals(q,statDate=str(context.current_dt)[:4])
    buylist =list(df['code'])
    #2，上市天数>750天
    buylist =delete_stock(buylist,context.current_dt,750)
    buylist =filter_paused_stock(buylist)[:20]
    
    return buylist


#过滤停牌股票
def filter_paused_stock(stock_list):
    current_date =get_current_data()
    
    return [stock for stock in stock_list if not current_date[stock].paused ]
    


##交易函数
def trade(context):
    if g.days%g.refresh_rate == 0:
        #白马股选股
        stockList = check_stocks(context)
        #获取当前持仓列表
        sell_list =list(context.portfolio.positions.keys())
        
        sells =list(set(sell_list).difference(set(stockList)))
        
        #先卖再买
        for stock in sells:
            order_target_value(stock,0)
            
            
        #分配资金
        if len(context.portfolio.positions)<g.stocknum:
            num =g.stocknum -len(context.portfolio.positions)
            cash =context.portfolio.cash/num
        else:
            cash=0;
        
        for stock in stockList:
            if len(context.portfolio.positions)<g.stocknum and stock not in context.portfolio.positions :
                order_value(stock,cash)
                
        #更新天数计数器
        g.days=1
    else:
        g.days +=1
## 开盘前运行函数     
def before_market_open(context):
    pass
    
## 开盘时运行函数
def market_open(context):
    pass
 
## 收盘后运行函数  
def after_market_close(context):
    pass
