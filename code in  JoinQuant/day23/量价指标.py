# 导入函数库
from jqdata import *
from jqlib.technical_analysis import *
#获取多支股票多日的OBV指标值
security_list=['000001.XSHE','000002.XSHE','601211.XSHG']
check_dates=['2022-10-31','2022-11-01','2022-11-02']
for check_date in check_dates:
    for stock in security_list:
        _OBV=OBV(stock,check_date=check_date,timeperiod=30)
        print(check_date,f'{stock}的OBV指为：',_OBV[stock])

print('---')
#获取多支股票多日的VOL指标值
security_list=['000001.XSHE','000002.XSHE']
check_dates=['2022-10-31','2022-11-01']
for check_date in check_dates:
    for stock in security_list:
        _VOL,MAVOL1,MAVOL2=VOL(stock,check_date=check_date,M1=5,M2=10)
        print(check_date,f'{stock}的VOL指为：',_VOL[stock])
        print(check_date,f'{stock}的MAVOL1指为：',MAVOL1[stock])
        print(check_date,f'{stock}的MAVOL2指为：',MAVOL2[stock])

print('---')

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
