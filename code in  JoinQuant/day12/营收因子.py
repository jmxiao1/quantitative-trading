# 导入函数库
from jqdata import *
#营业同比增长率大于300的股票代码
df =get_fundamentals(query(indicator.code,
                            indicator.inc_revenue_year_on_year
                            ).filter(
                                 indicator.inc_revenue_year_on_year >300
                                 ).order_by(indicator.inc_revenue_year_on_year.desc()),
                                 date='2022-09-01'

    )
print(df)

#打印这些股票近5日的每日最高价
df_new =history(5,unit='1d',field='high_limit',security_list=df['code'],df=True)
print(df_new)

#营业环比增长率大于900的股票代码
df1 =get_fundamentals(query(indicator.code,
                            indicator.inc_revenue_annual
                            ).filter(
                                 indicator.inc_revenue_annual >900
                                 ).order_by(indicator.inc_revenue_annual.desc()),
                                 date='2019-06-01'

    )
print(df1)

#营业总收入
df2 =get_fundamentals(query(indicator.code,
                            indicator.net_profit_to_total_revenue
                                 ).order_by(indicator.net_profit_to_total_revenue.desc()),
                                 date='2022-09-01'

    )
print(df2)

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
