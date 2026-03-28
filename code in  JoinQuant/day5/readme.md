发现聚宽的代码毕竟是python代码，所以之后还是上传python文件了，而且以这种方式上传学习笔记挺不错的，更适配而且更美观

##今日学习了策略信息，主要以context对象与Position对象为主

#1，context对象,为策略信息总览，包括账户信息，交易信息，策略信息，回测信息，时间等
包括以下属性：
- subportfolios：当前单个操作仓位的资金，标的信息，是一个SubPortfolio的数组
- portfolio:账户信息，即subportfolios的汇总信息，Portfolio对象，当个操作仓位时，portfolio指向sibportfolios[0]
- current_dt：当前单位时间的开始时间，[datetime.datetime]对象
- previous_date：前一个交易日,[datetime.date]对象，注意，这是一个日期，是date，而不是datetime
- universe:查询set_universe()设定的股票池，比如:['000001.XSHE','600000.XSHE']
-------------
#2.Position对象，为输出持有的标的的信息
包括以下属性：
- security：标的代码
- price：当前行情价格
- total_amount：当前持有的标的数量,即总仓位，不包括挂单冻结仓位
- init_time:建仓时间，格式为datetime.datetime