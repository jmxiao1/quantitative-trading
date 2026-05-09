from jqdata import *
import pandas as pd

def initialize(context):
    # 设定基准为中证500指数
    set_benchmark('000905.XSHG')
    set_option('use_real_price', True)
    # 设定手续费与滑点
    set_order_cost(OrderCost(close_tax=0.001, open_commission=0.0003, close_commission=0.0003, min_commission=5), type='stock')
    
    # --- 极限优化核心参数 ---
    g.stock_num = 10           # 目标持仓数量
    g.index = '000905.XSHG'    # 择时基准换为：中证500 (更贴近小市值生态)
    
    # 财务质量底线
    g.roe_threshold = 5.0
    g.roa_threshold = 3.0
    
    # 定期执行：每个月第一个交易日运行
    run_monthly(rebalance, monthday=1, time='09:30')

def check_market_timing(context):
    """
    择时模块升级：双均线多头排列确认趋势，告别假突破
    """
    # 获取过去 60 天的指数收盘价
    hist = attribute_history(g.index, 60, '1d', ['close'])
    
    # 计算快线 (20日) 和 慢线 (60日)
    ma20 = hist['close'][-20:].mean()
    ma60 = hist['close'].mean()
    
    # 只有当快线在慢线之上 (多头趋势确立) 时，才判定为安全
    return ma20 > ma60

def filter_basic_stocks(context, stock_list):
    """
    基础排雷
    """
    current_data = get_current_data()
    stock_list = [s for s in stock_list if not current_data[s].paused and not current_data[s].is_st]
    stock_list = [s for s in stock_list if (context.current_dt.date() - get_security_info(s).start_date).days > 250]
    return stock_list

def rebalance(context):
    """
    核心调仓逻辑：基本面初筛 -> 市值排序 -> 动量终选
    """
    # ================= 1. 宏观风控判断 =================
    is_safe = check_market_timing(context)
    
    if not is_safe:
        print(f"{context.current_dt.date()}: 中证500双均线死叉，执行【纯现金空仓】防守。")
        for stock in context.portfolio.positions:
            order_target_value(stock, 0)
        return

    print(f"{context.current_dt.date()}: 中证500多头确认，执行【动量小市值】进攻。")
    
    # ================= 2. 基础选股池 =================
    all_stocks = list(get_all_securities(['stock']).index)
    pool = filter_basic_stocks(context, all_stocks)
    
    # ================= 3. 质量+市值双重过滤 =================
    # 先放大基数，选出满足财务条件且市值最小的 100 只候选股
    q = query(
        valuation.code
    ).filter(
        valuation.code.in_(pool),
        indicator.roe > g.roe_threshold,
        indicator.roa > g.roa_threshold
    ).order_by(
        valuation.market_cap.asc()
    ).limit(100)
    
    df_fund = get_fundamentals(q)
    target_pool = list(df_fund['code'])
    
    if not target_pool:
        return
        
    # ================= 4. 个股动量增强 (精选强者) =================
    # 获取这 100 只股票过去 20 天的收盘价
    hist_prices = history(20, '1d', 'close', target_pool)
    
    momentum_dict = {}
    for stock in target_pool:
        # 计算 20 日收益率作为动量指标
        ret_20d = (hist_prices[stock][-1] - hist_prices[stock][0]) / hist_prices[stock][0]
        momentum_dict[stock] = ret_20d
        
    # 将字典按动量值从大到小排序，提取前 10 只最强势的股票
    sorted_stocks = sorted(momentum_dict.items(), key=lambda item: item[1], reverse=True)
    buy_list = [stock for stock, momentum in sorted_stocks][:g.stock_num]
    
    # ================= 5. 执行调仓 =================
    # 卖出不在最新买入列表中的股票
    for stock in context.portfolio.positions:
        if stock not in buy_list:
            order_target_value(stock, 0)
            
    # 等权重买入
    if len(buy_list) > 0:
        target_value = context.portfolio.total_value / len(buy_list)
        for stock in buy_list:
            order_target_value(stock, target_value)