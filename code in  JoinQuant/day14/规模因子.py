# 导入函数库
from jqdata import *

#总市值大于10000亿的股票代码Top5
df =get_fundamentals(query(
                        valuation.code,
                        valuation.market_cap
                        ).filter(
                            valuation.market_cap>10000
                            ).order_by(valuation.market_cap.desc())
    )
print(df[:5])

#流通市值大于5000亿的股票代码Top5
df1 =get_fundamentals(query(
                        valuation.code,
                        valuation.circulating_market_cap
                        ).filter(
                            valuation.circulating_market_cap>5000
                            ).order_by(valuation.circulating_market_cap.desc())
    )
print(df1[:5])

#总股本大于1000亿股，总市值大于8000亿的股票代码Top5
df2 =get_fundamentals(query(
                        valuation.code,
                        valuation.capitalization,
                        valuation.market_cap
                        ).filter(
                            valuation.capitalization >10000000,
                            valuation.market_cap>8000
                            ).order_by(valuation.capitalization.desc())
    )
print(df2[:5])

#流通股本大于1000亿股，流通市值大于5000亿的股票代码Top5
df3 =get_fundamentals(query(
                        valuation.code,
                        valuation.circulating_cap,
                        valuation.circulating_market_cap
                        ).filter(
                            valuation.circulating_cap >10000000,
                            valuation.circulating_market_cap>5000
                            ).order_by(valuation.circulating_cap.desc())
    )
print(df3[:5])

# 初始化函数，设定基准等等
def initialize(context):
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
