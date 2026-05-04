# 导入聚宽函数库
from jqdata import *

def initialize(context):
    # 设定基准为中证500指数 (小市值策略通常以中证500或中证1000为基准)
    set_benchmark('000905.XSHG')
    # 使用真实价格回测
    set_option('use_real_price', True)
    # 设定手续费与滑点
    set_order_cost(OrderCost(close_tax=0.001, open_commission=0.0003, close_commission=0.0003, min_commission=5), type='stock')
    
    # 策略核心参数
    g.stock_num = 10  # 每次买入市值最小的10只股票
    
    # 定期执行：每个月第一个交易日的 09:30 执行调仓
    run_monthly(rebalance, monthday=1, time='09:30')

def filter_basic_stocks(context, stock_list):
    """
    基础排雷过滤：这是经典策略里仅有的一层防护
    剔除停牌、ST、*ST、上市不足一年的次新股
    """
    current_data = get_current_data()
    
    # 1. 剔除停牌
    stock_list = [stock for stock in stock_list if not current_data[stock].paused]
    # 2. 剔除 ST、*ST 股票 (防止直接退市)
    stock_list = [stock for stock in stock_list if not current_data[stock].is_st]
    # 3. 剔除上市不足 250 天的次新股 (次新股市值虽小但波动极度异常)
    stock_list = [stock for stock in stock_list if (context.current_dt.date() - get_security_info(stock).start_date).days > 250]
    
    return stock_list

def rebalance(context):
    """
    核心调仓逻辑：简单粗暴地按总市值升序排列
    """
    # 1. 获取全市场股票代码
    all_stocks = list(get_all_securities(['stock']).index)
    
    # 2. 基础排雷过滤
    pool = filter_basic_stocks(context, all_stocks)
    
    # 3. 核心查询：在过滤后的股票池中，按总市值从小到大排序，取前 N 只
    q = query(
        valuation.code,
        valuation.market_cap
    ).filter(
        valuation.code.in_(pool)
    ).order_by(
        valuation.market_cap.asc()
    ).limit(
        g.stock_num
    )
    
    # 执行查询获取 dataframe
    df = get_fundamentals(q)
    
    # 提取最终要买入的股票代码列表
    buy_list = list(df['code'])
    
    # 4. 执行卖出逻辑：如果当前持仓的股票不在最新的 buy_list 中，则全部卖出
    for stock in context.portfolio.positions:
        if stock not in buy_list:
            order_target_value(stock, 0)
            
    # 5. 执行买入逻辑：将账户总资产平均分配到这 N 只股票上
    if len(buy_list) > 0:
        # 计算每只股票的目标持仓金额
        target_value = context.portfolio.total_value / len(buy_list)
        
        for stock in buy_list:
            # 无论当前是否已持有，直接将该股票的仓位调整到目标金额
            order_target_value(stock, target_value)