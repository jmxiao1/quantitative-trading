## 今日学习量化交易数据获取之获取股票财务数据，主要从四个方面学习：get_fundamentals()函数，query_object,get_fundamentals_continuously()函数，以及代码实战
----------------
1. get_fundamental()函数：查询财务数据，主要格式为get_fundamentals(query_object,date=None,statDate=None)
- 注意：date和statDate参数只能传入一个，传入date时，查询指定日期date收盘后所能看到的最近(除市值表外为最近一个季度，市值表为最近一天)的数据
- 传入statDate时，查询statDate指定的季度或者年份的财务数据
- date/statDate：获取一个字符串(格式类似'2015-10-15')或者datetime对象
- query_object：一个sqlalchemy.orm.query.Query对象，用于查询数据库，具体格式为：query_object = query(StockBasics).filter(StockBasics.code == '000001'),可以通过全局的query函数获取Query对象

2. query_object:query()可查询数据API，可以是整张表，也可以是表中的多个字段或者计算出的结果，包括：
- filter()：填写过滤条件，多个过滤条件可用逗号隔开，或者and,or，如：query_object.filter(StockBasics.code == '000001')
- order_by()：填写排序条件，如：query_object.order_by(StockBasics.code)
- limit()：填写返回条数，限制返回的个数，如：query_object.limit(10)
- group_by:分组统计
例如：query(valuation).filter(valuation.code='000001').order_by(valuation.code).limit(10) 
- 查询'000001'股票的市值表，并按股票代码排序，返回前10条数据

3. get_fundamentals_continuously()函数：查询多日财务数据，主要格式为get_fundamentals_continuously(query_object, end_date=None,count=None, panel=True,),包括：
- end_date：获取一个字符串(格式类似'2015-10-15')或者datetime对象，获取指定日期之前的数据
- count：获取end_date前的count个数据，默认为None，获取所有数据，count须小于500
- panel：默认panel=True，返回一个Panel对象，否则返回一个等效的DataFrame对象，建议设置panel为False
