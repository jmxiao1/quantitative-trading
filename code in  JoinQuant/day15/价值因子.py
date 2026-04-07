# 导入函数库
from jqdata import *
#市净率小于1.5，总市值大于8000亿的股票代码
df=get_fundamentals(query(
                    valuation.code,
                    valuation.pb_ratio,#市净率
                    valuation.market_cap
                    ).filter(
                        valuation.pb_ratio<1.5,
                        valuation.market_cap>8000
                        ).order_by(valuation.pb_ratio.asc())
                        ,date='2022-09-01'
                )
print(df[:5])

#市净率小于1.5，市销率小于1.5的股票代码
df1=get_fundamentals(query(
                    valuation.code,
                    valuation.pb_ratio,
                    valuation.ps_ratio
                    ).filter(
                        valuation.pb_ratio<1.5,
                        valuation.ps_ratio<0.5#市销率
                        ).order_by(valuation.ps_ratio.asc())
                        ,date='2019-09-01'
                )
print(df1[:5])

#动态市盈率小于6，市销率小于0.5，静态市盈率在3-5的股票代码，按照静态市盈率排序
df2=get_fundamentals(query(
                    valuation.code,
                    valuation.pcf_ratio,#动态市盈率
                    valuation.pe_ratio,#静态市盈率
                    valuation.ps_ratio
                    ).filter(
                        valuation.pcf_ratio<6,
                        valuation.pe_ratio>3,
                        valuation.pe_ratio<5,
                        valuation.ps_ratio<0.5
                        ).order_by(valuation.pe_ratio.asc())
                        ,date='2019-09-01'
                )
print(df2[:5])




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