今日学习账户信息，主要以Portfolio与SubPortfolio为主，其他信息为辅，具体如下：

1. Portfolio对象：为总账户信息，包括：
- long_positions:多单的仓位，一个dict,key是证券代码,value是[Position]对象
- short_positions:空单的仓位，一个dict,key是证券代码,value是[Position]对象
- total_value:总的权益，包括现金，保证金(期货)或者仓位(股票)的总价值，可用来计算收益
- returns: 总权益的累计收益；(当前总资产+今日出入金-昨日总资产)/昨日总资产
- staring_cash: 初始资金,现在等于inout_cash
- positions_value:持仓价值，包括多单和空单

2. SubPortfolio对象：为子账户信息，包括：
- inout_cash:累计出入金，如初始资金1000，后来转移出去100，则这个值为1000-100
- available_cash:可用资金，包括现金和保证金(期货)或者仓位(股票)的总价值，可用来计算收益,也可用来购买证券的资金
- transferable_cash:可取资金，即可用提现的资金，不包括今日卖出证券所得资金
- locked_cash:挂单锁住资金
- type:账户所属类型
 