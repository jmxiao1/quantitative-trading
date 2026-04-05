# 导入函数库
from jqdata import *

#净利润同比增长率大于300股票代码
df= get_fundamentals(query(
                    indicator.code,
                    indicator.inc_net_profit_year_on_year
                    ).filter(
                        indicator.inc_net_profit_year_on_year >300
                        ).order_by(indicator.inc_net_profit_year_on_year.desc())
                        ,date='2022-09-01'
    )
print(df)

#净利润环比增长率大于500股票代码
df1= get_fundamentals(query(
                    indicator.code,
                    indicator.inc_net_profit_annual
                    ).filter(
                        indicator.inc_net_profit_annual >500
                        ).order_by(indicator.inc_net_profit_annual.desc())
                        ,date='2022-09-01'
    )
print(df1[:5])

#营业利润率大于200股票代码
df2= get_fundamentals(query(
                    indicator.code,
                    indicator.operation_profit_to_total_revenue
                    ).filter(
                        indicator.operation_profit_to_total_revenue >200
                        ).order_by(indicator.operation_profit_to_total_revenue.desc())
                        ,date='2022-09-01'
    )
print(df2[:5])

#营业净利润率最高的5个股票代码
df3= get_fundamentals(query(
                    indicator.code,
                    indicator.net_profit_margin
                    ).order_by(indicator.net_profit_margin.desc())
                        ,date='2022-09-01'
    )
print(df3[:5])

#销售毛利润最高的5个股票代码
df4= get_fundamentals(query(
                    indicator.code,
                    indicator.gross_profit_margin
                    ).order_by(indicator.gross_profit_margin.desc())
                        ,date='2022-09-01'
    )
print(df4[:5])
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
