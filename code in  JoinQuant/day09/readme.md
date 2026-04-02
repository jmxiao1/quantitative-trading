今日学习标的信息，主要包括以下几个方面:1.获取所有标的信息，2.获取单个标的信息,3.代码实战
----------
1.获取所有标的信息：指可以获得平台支持的所有股票，基金，指数，期货，期权信息，python代码为get_all_securities(types=[],date=None)
- types：指定标的类型，默认为所有类型，可选参数为['stock','index','fund','future','option']
- date：指定日期，默认为当天，格式为YYYY-MM-DD
- 返回值：一个包含所有标的信息的DataFrame，每一行代表一个标的，包含以下列：
    - code：标的代码
    - name：标的名称
    - start_date：标的上市日期
    - end_date：标的退市日期

- 注：stock为股票，index为指数，fund为基金，future为期货，option为期权

----------
2.获取单个标的信息：指可以获得单个指定标的的详细信息，包括中文名称，简称，上市日期，退市日期，标的种类等，python代码为get_security_info(code,date=None)
- code：指定标的代码，格式为字符串
- date：指定日期，默认为当天，格式为YYYY-MM-DD
- 返回值：一个包含单个标的信息的DataFrame，每一行代表一个标的，包含以下列：
    - code：标的代码
    - name：标的名称
    - start_date：标的上市日期
    - end_date：标的退市日期
    - type：标的类型
    - category：标的分类
    - market：标的所在市场
    - board：标的所在板块
    - industry：标的所在行业

