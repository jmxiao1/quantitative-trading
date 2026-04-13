# 导入函数库
from jqdata import *
from jqlib.technical_analysis import *
#获取多只股票的RSI值
security_list=['000001.XSHE','000002.XSHE','601211.XSHG']
_RSI=RSI(security_list,check_date='2022-09-01',unit='1d',N1=6)
for stock in security_list:
    print(stock,"2022-09-01日的RSI的值为",_RSI[stock])


print('-------')    

#获取单只股票多日的WR指标值
security1='601311.XSHG'
check_dates1=['2022-10-31','2022-11-01','2022-10-02']
for check_date in check_dates1:
    _WR,MAWR=WR(security1,check_date=check_date,unit='1d',N=10,N1=3)
    print( check_date,"WR的值为",_WR[security1])
    print( check_date,"MAWR的值为",MAWR[security1])
   
print('-------') 

##获取单只股票多日的KDJ指标值
security2= '000001.XSHE'
check_dates2=['2022-09-05','2022-09-06','2022-09-07']
for check_date in check_dates2:
    K,D,J=KDJ(security2,check_date=check_date,unit='1d',N=9,M1=3,M2=3)
    print( check_date,"K值为",K[security2])
    print( check_date,"D的值为",D[security2])
    print( check_date,"J的值为",J[security2])

    
   
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
