# 导入函数库
from jqdata import *
from jqlib.technical_analysis import *
#获取单只股票三天的5，10，20日均线
security='000001.XSHE'
check_dates=['2022-09-05','2022-09-06','2022-09-07']
for check_date in check_dates:
    MA5=MA(security,check_date=check_date,timeperiod=5)
    MA10=MA(security,check_date=check_date,timeperiod=10)
    MA20=MA(security,check_date=check_date,timeperiod=20)

    print(check_date,"5日均线：",MA5[security])
    print(check_date,"10日均线：",MA10[security])
    print(check_date,"20日均线：",MA20[security])


#获取单只股票三天的6，12，24，72日变异均线
security1='000001.XSHE'
check_dates=['2022-09-05','2022-09-06','2022-09-07']
for check_date in check_dates:
    _VMA6=VMA(security1,check_date=check_date,timeperiod=6)
    _VMA12=VMA(security1,check_date=check_date,timeperiod=12)
    _VMA24=VMA(security1,check_date=check_date,timeperiod=24)
    _VMA72=VMA(security1,check_date=check_date,timeperiod=72)

    print(check_date,"6日变异均线：", _VMA6[security1])
    print(check_date,"12日变异均线：",_VMA12[security1])
    print(check_date,"24日变异均线：",_VMA24[security1])
    print(check_date,"72日变异均线：",_VMA72[security1])
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
