学习了交易函数里的交易对象：order对象与trade对象。
order对象：主要是存储订单处理流程，包括订单创建-订单检查-报单-确认委托-撮合。参数包括commission(交易费用，即佣金，税费等）,is_buy(bool值，买还是卖），status(状态，一个OrderStatus值），
price（平均成交价格）。

Trade:存储订单成交信息，包括time(交易时间），security（标的代码），amount（交易数量），price(交易价格），trade_id（交易记录id），order_id(对应订单id)