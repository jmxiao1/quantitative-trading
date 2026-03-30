# 导入函数库
from jqdata import *
#单日或单季度的财务报告
q=query(valuation).filter(valuation.code=='000001.XSHE')
df=get_fundamentals(q,'2022-09-01')
print(df['market_cap'][0])

p=query(income.statDate,
        income.code,
        income.basic_eps
        ).filter(income.code=='000001.XSHE')

rets =get_fundamentals(p,statDate='2022q2')
print(rets)

q2=query(valuation.market_cap,
         valuation.pe_ratio,
         valuation.turnover_ratio,
         indicator.eps
         ).filter(valuation.code.in_(['000001.XSHE ','600000.XSHG']))
         
result =get_fundamentals_continuously(q2,end_date='2022-01-01',count=5,panel=False)

print(result)
def initialize(context):
    # 设定沪深300作为基准
    set_benchmark('000300.XSHG')
    # 开启动态复权模式(真实价格)
    pass
## 开盘前运行函数     
def before_market_open(context):
    pass
    
## 开盘时运行函数
def market_open(context):
    pass
 
## 收盘后运行函数  
def after_market_close(context):
    pass