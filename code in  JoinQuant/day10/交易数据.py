# 导入函数库
from jqdata import *

##获取一支股票
#获取000001.XSHE的股票数据
df = get_price('000001.XSHE')
print(df)

#获取000001.XSHE的2015年1月的股票数据
df1 = get_price('000001.XSHE',start_date = '2015-01-01',end_date='2015-01-31 23:00:00',frequency='1m',fields=['open','close'])
print(df1)

#获取000001.XSHE的2016年3月的股票数据
df2 = get_price('000001.XSHE',start_date = '2016-03-01',end_date='2015-03-31 23:00:00',frequency='1m',fields=['open','close'])
print(df2)
##------------

##获取多支股票
#获取中证100所有的股票数据
df3= get_price(get_index_stocks('000903.XSHG'),panel=False)
print(df3)
print(df3.loc[df3['code']=='000001.XSHE'])
##-----------

##获取龙虎榜数据
#获取2022-09-01的龙虎榜数据
df4=get_billboard_list(stock_list=None,end_date='2022-09-01',count=1)
print(df4)
#获取2022-09-01的2个交易日龙虎榜数据
df5=get_billboard_list(stock_list=None,end_date='2022-09-01',count=2)
print(df[['code','abnormal_name','sales_depart_name','rank']][:10])
# 初始化函数，设定基准等等
def initialize(context):
   pass
## 开盘前运行函数     
def before_market_open(context):
    pass