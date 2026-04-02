今日学习交易数据，包括:1，获取行情信息，2，获取龙虎榜信息，3，代码实战
------
1.获取行情信息：即获取证券行情数据，可查询多个标的多个数据字段，python代码为get_price(security,start_date=None,end_ddate=None,frequency='daily',fields=None,skip_paused=False,fq='pre',panel=False,count=None,fill_paused=True)
- security:一只股票代码或者一个股票代码list，
- count:与start_date二选一，不可同时使用。数量，返回的结果集的行数，表示获取end_date前的多少个frequency的数据，默认为None
- start_date:与count二选一，不可同时使用。为字符串或者datetime对象，表示开始日期，格式为'YYYY-MM-DD'
- end_date:同start_date,表示结束日期
- frequency:即单位时间长度，表示数据频率，几天或者几分钟。可取值为'daily'，'minute'，'weekly'，'monthly'，现在支持'Xd','Xm',X表示一个正整数。
- fields:即字符串list，选择要获取的行情数据字段，表示返回数据中包含哪些字段，可取值为'open','high','low','close','volume','money','factor','high_limit','low_limit','pre_close','paused','open_interest'等，默认为None，表示返回所有字段
- skip_paused:即布尔值，是否跳过停牌数据(包括停牌，未上市或者退市后的日期)，默认为False，表示不跳过
- fq:即字符串，复权方式(对股票/基金的价格字段，成交量字段以及factor字段生效)，可取值为'pre'，'post'，'none'，默认为'pre'，表示前复权
- panel:获取多标的数据时建议设置panel为False，在pandas 0.25版后，panel被彻底移除
- fill_paused：对于停牌股票的价格处理，默认为True；True表示用pre_close填充，False表示用前一个交易日的数据填充
-------
2.龙虎榜信息：即获取龙虎榜数据，python代码为get_billboard_list(stock_list, start_date, end_date,count=None)
- stock_list:股票代码list，表示要获取的股票代码,当值为None时，返回指定日期的所有股票
- start_date:开始日期
- end_date:结束日期
- count：交易日数量，可以与end_date同时使用，表示获取end_date前count个交易日的数据(含end_date当日)，默认为None