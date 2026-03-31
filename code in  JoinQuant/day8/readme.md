今日学习如何获取成分股数据，主要以三个方面为参考：1.指数成分股函数，2.行业成分股函数，3.概念成分股函数
---------
1.指数成分股函数：查询指定指数指定日期可交易的成分股列表，python代码为get_index_stocks(index_symbol,date=None),包括以下参数
- index_symbol：指数代码，如上证50、沪深300、中证500等
- date/statdate：指定日期，默认为None，即获取一个字符串(格式类似'2015-10-15')或者datetime对象
- 返回：返回股票的代码list

2.行业成分股函数：查询指定行业指定日期可交易的所有股票，python代码为get_industry_stocks(industry_code,date=None),包括以下参数
- industry_code：行业代码，如“能源、原材料、工业、可选消费、主要消费、金融、房地产、医疗保健、信息技术、电信业务、公用事业、原材料”等
- date/statdate：指定日期，默认为None，即获取一个字符串(格式类似'2015-10-15')或者datetime对象
- 返回：返回股票的代码list

3.概念成分股函数：查询指定概念板块的所有股票，python代码为get_concept_stocks(concept_code,date=None),包括以下参数
- concept_code:行业编码
- date/statdate：指定日期，默认为None，即获取一个字符串(格式类似'2015-10-15')或者datetime对象
- 返回：返回股票的代码list
