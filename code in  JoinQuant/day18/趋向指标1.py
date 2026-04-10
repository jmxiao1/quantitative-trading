# 导入函数库
from jqdata import *
from jqlib.technical_analysis import *

#获取平安银行2022-09-01的macd
security='000001.XSHE'
DIF,DEA,_MACD= MACD(security_list=security,check_date='2022-09-01',
                    SHORT=12,LONG=26,MID=9)
print(DIF)
print(DEA)
print(_MACD)

print('---------------')
#获取多只股票的EMA
security_list1=['000001.XSHE','000002.XSHE','601211.XSHG']
EMV,MAEMV= EMV(security_list=security_list1,check_date='2022-09-01',
                N=14,M=9)
print(EMV)
print(MAEMV)

print('---------------')
#获取单只股票的UOS
security1='000001.XSHE'
UOS,MAUOS= UOS(security_list=security1,check_date='2022-09-01',
                N1=7,N2=14,N3=28,M=6)
print(UOS)
print(MAUOS)





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