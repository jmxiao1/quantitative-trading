# 导入函数库
from jqdata import *
#获得多只股票的GDX指标
from jqlib.technical_analysis import *
security_list=['000001.XSHE','000002.XSHE','601211.XSHG']
JAX,YLK,ZCX=GDX(security_list,check_date='2022-09-01',N=14,M=9)
for stock in security_list:
    print(stock,"济安线的值为：",JAX[stock])
    print(stock,"压力线的值为：",YLK[stock])
    print(stock,"支撑线的值为：",ZCX[stock])
    
#获取单只股票的JS指数
security='000001.XSHE'
_JS,MAJS1,MAJS2,MAJS3=JS(security,check_date='2022-09-01',N=5,M1=5,M2=10,M3=20)
print(_JS)
print(MAJS1)
print(MAJS2)
print(MAJS3)




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
