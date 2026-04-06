今日学习规模类因子，包括1，规模类因子介绍，2，总市值，3，流通市值，4，总股本，5，流通股本，6，代码实战
---
1，规模类因子介绍
规模类因子反映公司规模情况，注要用于体现市值大小对投资收益的影响，一般而言，市值越大，投资收益越高。
对应指标有：总市值，流通市值，总股本，流通股本
2，总市值
总市值指在某特定时间内股票总价值，用来表示个股权重大小或大盘的规模大小
- 计算方法：总市值=总股本*收盘价
- 代码：get_fundamentals(query(valuation.market.cap).filter({查询条件},date=({查询日期})))
3，流通市值
流通市值指在特定时间内当时可以交易流通股票总价值，流通市值占总市值的比重越大，说明股票的市场价格越能反映公司的真实价值。
- 流通市值=可交易的流通股本*收盘价
- 代码：get_fundamentals(query(valuation.circulating_market_cap).filter({查询条件},date=({查询日期})))
4，总股本
总股本指公司已发行的普通股股票股份总数(包括A股，B股和H股的总股本)，单位万股
- 代码：get_fundamentals(query(valuation.capitalization).filter({查询条件},date=({查询日期})))
5，流通股本
流通股本指公司已发行的境内上市流通，以人民币兑换的股份总数，即A股市场的流通股本，单位万股
- 代码：get_fundamentals(query(valuation.circulating_cap).filter({查询条件},date=({查询日期})))