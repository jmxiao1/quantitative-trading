# 导入函数库
from jqdata import *

#净资产收益率大于50的股票代码,降序排序
df= get_fundamentals(query(
                            indicator.code,
                            indicator.roe
                            ).filter(
                                indicator.roe>50).order_by(indicator.roe.asc())
                    ,date='2019-03-01'
            )
print(df)

#总资产收益率大于10的股票代码，降序排列
df1=get_fundamentals(query(
                    indicator.code,indicator.roa)
                    .filter(indicator.roa>10)
                    .order_by(indicator.roa.asc())
                    )
print(df1)
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