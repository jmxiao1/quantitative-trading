# 导入函数库
from jqdata import *

# 初始化函数，设定基准等等
def initialize(context):
    # 设定沪深300作为基准
    set_benchmark('000300.XSHG')
    g.security ='000001.XSHE'

def handle_data(context, data):
       if g.security not in context.portfolio.positions:
        orders =order(g.security,1000) 
       else:
        order(g.security,-800)
    
       print("""多单的仓位：{}""".format(context.portfolio.long_positions))
       print("""空单的仓位：{}""".format(context.portfolio.short_positions))
       print("""总权益：{}""".format(context.portfolio.total_value))
       print("""总权益的累计收益：{}""".format(context.portfolio.returns))
       print("""初始资金：{}""".format(context.portfolio.starting_cash))
       print("""持仓价值：{}""".format(context.portfolio.positions_value))

       print("""累计出入金：{}""".format(context.subportfolios[0].inout_cash))
       print("""可用资金：{}""".format(context.subportfolios[0].available_cash))
       print("""可取资金：{}""".format(context.subportfolios[0].transfer_cash))
       print("""挂单锁住资金：{}""".format(context.subportfolios[0].locked_cash))
       print("""账户所属类型：{}""".format(context.subportfolios[0].type))