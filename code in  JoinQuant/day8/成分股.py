# 导入函数库
from jqdata import *

# 返回沪深300的股票（100个）
stock =get_index_stocks('000300.XSHG')
print(stock[0:100])

#获取计算机/互联网行业的成分股
stock1=get_industry_stocks('I64')
print(stock1)

#获取风电板块概念板块的成分股
stock2=get_concept_stocks('sc0084',date='2022-06-01')
print(stock2)
## 开盘前运行函数     
def before_market_open(context):
    pass
    
## 开盘时运行函数
def market_open(context):
    pass
 
## 收盘后运行函数  
def after_market_close(context):
    pass
