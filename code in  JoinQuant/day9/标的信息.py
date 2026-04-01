# 导入函数库
from jqdata import *

#获取平台所有标的信息，返回前十
print(get_all_securities()[:10])

#获取平台所有ETF信息，返回前十
print(get_all_securities(types=['etf'],date='2022-09-01')[:10])

#获取000001.XSHE的标的信息
start_date =get_security_info('000001.XSHE').start_date
print(start_date)
type =get_security_info('000001.XSHE').type
print(type)
print(get_security_info('000001.XSHE'))


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
