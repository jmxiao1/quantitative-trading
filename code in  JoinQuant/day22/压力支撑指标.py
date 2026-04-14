# 导入函数库
from jqdata import *
from jqlib.technical_analysis import *
#获取单支股票三天的BOLL指标值
security='600031.XSHG'
check_dates=['2022-10-31','2022-11-01','2022-11-02']
for check_date in check_dates:
    upper,middle,lower=Bollinger_Bands(security,check_date=check_date,timeperiod=20,nbdevup=2,nbdevdn=2)
    print(check_date,f'{security}上轨道线值为:',upper[security])
    print(check_date,f'{security}中轨道线值为:',middle[security])
    print(check_date,f'{security}下轨道线值为:',lower[security])

print('------')
#获取单支股票两天的MIKE指标值
security='600031.XSHG'
check_dates=['2022-10-31','2022-11-01']
for check_date in check_dates:
    storl,midrl,wekrl,weksl,midsl,stosl=MIKE(security,check_date=check_date,timeperiod=10)#timeperiod>10都会报错，这是聚宽函数的bug
    print(check_date,f'{security}storl值为:',storl[security])
    print(check_date,f'{security}midrl值为:',midrl[security])
    print(check_date,f'{security}wekrl值为:',wekrl[security])
    print(check_date,f'{security}stosl值为:',stosl[security])
    print(check_date,f'{security}midsl值为:',midsl[security])
    print(check_date,f'{security}weksl值为:',weksl[security])

print('------')

#获取单支股票两天的XS指标值
security='000001.XSHE'
check_dates=['2022-10-31','2022-11-01']
for check_date in check_dates:
    SUP,SDN,LUP,LDN=XS(security,check_date=check_date,timeperiod=13)
    print(check_date,f'{security}SUP值为:',SUP[security])
    print(check_date,f'{security}SDN值为:',SDN[security])
    print(check_date,f'{security}LUP值为:',LUP[security])
    print(check_date,f'{security}LDN值为:',LDN[security])

print('------')


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
