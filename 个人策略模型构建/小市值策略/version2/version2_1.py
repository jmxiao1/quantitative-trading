from jqdata import *
import pandas as pd
import numpy as np

def initialize(context):
    # 设定基准为中证500指数
    set_benchmark('000905.XSHG')
    set_option('use_real_price', True)
    # 设定手续费与滑点
    set_order_cost(OrderCost(close_tax=0.001, open_commission=0.0003, close_commission=0.0003, min_commission=5), type='stock')
    
    # --- 优化后的核心参数 ---
    g.stock_num = 10           # 目标持仓数量
    g.index = '000905.XSHG'    # 择时基准：中证500
    
    # 财务质量底线
    g.roe_threshold = 5.0
    g.roa_threshold = 3.0
    
    # ========== 1. 优化：动量时间窗口（30日） ==========
    g.momentum_window = 30     # 动量计算窗口从20日改为30日
    
    # ========== 2. 优化：市值筛选范围（避免极端小市值） ==========
    g.min_market_cap = 10      # 最小市值（亿）
    g.max_market_cap = 200     # 最大市值（亿）
    
    # ========== 3. 优化：止损参数 ==========
    g.stop_loss_pct = -0.10    # 止损阈值：-10%
    
    # ========== 4. 择时参数（修复版：更宽松实用） ==========
    g.enable_timing = True      # 择时开关（可手动关闭）
    g.timing_mode = 'ma'        # 'ma'=均线, 'rsi'=RSI, 'macd'=MACD, 'none'=不择时
    
    # 择时阈值（宽松设置，避免全年空仓）
    g.ma_short = 20             # 短期均线
    g.ma_long = 60              # 长期均线
    g.rsi_threshold = 40        # RSI低于40视为超卖可入场（放宽到40）
    
    # 定期执行：周度调仓
    run_weekly(rebalance, weekday=1, time='09:35')

def check_market_timing_practical(context):
    """
    实用择时模块（修复版）：多种模式可选，避免全年空仓
    返回: True=进攻, False=防守
    """
    # 如果不启用择时，始终进攻
    if not g.enable_timing:
        return True
    
    # 获取过去120天的指数数据
    hist_data = attribute_history(g.index, 120, '1d', ['close'])
    hist_close = hist_data['close']
    
    current_price = hist_close.iloc[-1]
    ma_short = hist_close[-g.ma_short:].mean()
    ma_long = hist_close[-g.ma_long:].mean()
    
    # ===== 模式1：简单均线择时（推荐，不易全年空仓） =====
    if g.timing_mode == 'ma':
        # 宽松条件：价格 > 长期均线 或 短期均线 > 长期均线
        is_safe = (current_price > ma_long) or (ma_short > ma_long)
        
        print(f"{context.current_dt.date()}: 【均线择时】价格={current_price:.2f}, MA{g.ma_long}={ma_long:.2f}, "
              f"MA{g.ma_short}={ma_short:.2f}, 信号={'进攻' if is_safe else '防守'}")
        
        return is_safe
    
    # ===== 模式2：RSI择时（捕捉超卖反弹） =====
    elif g.timing_mode == 'rsi':
        # 计算RSI
        delta = hist_close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        current_rsi = rsi.iloc[-1]
        
        # RSI > 40 或 从超卖区反弹
        is_safe = current_rsi > g.rsi_threshold
        
        print(f"{context.current_dt.date()}: 【RSI择时】RSI={current_rsi:.1f}, 阈值={g.rsi_threshold}, "
              f"信号={'进攻' if is_safe else '防守'}")
        
        return is_safe
    
    # ===== 模式3：MACD择时 =====
    elif g.timing_mode == 'macd':
        # 计算MACD
        exp1 = hist_close.ewm(span=12, adjust=False).mean()
        exp2 = hist_close.ewm(span=26, adjust=False).mean()
        macd_dif = exp1 - exp2
        macd_dea = macd_dif.ewm(span=9, adjust=False).mean()
        
        # 宽松条件：DIF > DEA 或 DIF在0轴上方
        is_safe = macd_dif.iloc[-1] > macd_dea.iloc[-1] or macd_dif.iloc[-1] > 0
        
        print(f"{context.current_dt.date()}: 【MACD择时】DIF={macd_dif.iloc[-1]:.3f}, DEA={macd_dea.iloc[-1]:.3f}, "
              f"信号={'进攻' if is_safe else '防守'}")
        
        return is_safe
    
    # ===== 模式4：不择时（始终满仓） =====
    else:
        return True

def check_stop_loss(context, holding_stock):
    """
    止损机制
    """
    if holding_stock not in context.portfolio.positions:
        return False
    
    position = context.portfolio.positions[holding_stock]
    if position.total_amount == 0:
        return False
    
    avg_cost = position.avg_cost
    current_price = get_current_data()[holding_stock].last_price
    
    if avg_cost > 0:
        pnl_pct = (current_price - avg_cost) / avg_cost
        
        if pnl_pct <= g.stop_loss_pct:
            print(f"{context.current_dt.date()}: 【止损触发】{holding_stock} 亏损{pnl_pct:.2%}，强制卖出")
            order_target_value(holding_stock, 0)
            return True
    
    return False

def filter_basic_stocks(context, stock_list):
    """
    基础排雷
    """
    current_data = get_current_data()
    
    stock_list = [s for s in stock_list if not current_data[s].paused and not current_data[s].is_st]
    stock_list = [s for s in stock_list if (context.current_dt.date() - get_security_info(s).start_date).days > 250]
    
    return stock_list

def filter_by_market_cap(stock_list):
    """
    市值筛选
    """
    if not stock_list:
        return []
    
    q = query(
        valuation.code, 
        valuation.market_cap
    ).filter(
        valuation.code.in_(stock_list)
    )
    
    df_mcap = get_fundamentals(q)
    
    filtered = df_mcap[
        (df_mcap['market_cap'] >= g.min_market_cap) & 
        (df_mcap['market_cap'] <= g.max_market_cap)
    ]
    
    return list(filtered['code'])

def rebalance(context):
    """
    核心调仓逻辑
    """
    # ================= 1. 择时判断（实用版） =================
    is_safe = check_market_timing_practical(context)
    
    if not is_safe:
        print(f"{context.current_dt.date()}: 市场信号偏空，执行【现金空仓】防守。")
        for stock in context.portfolio.positions:
            order_target_value(stock, 0)
        return
    
    print(f"{context.current_dt.date()}: 市场信号偏多，执行【优化动量小市值】进攻。")
    
    # ================= 2. 止损检查 =================
    for stock in list(context.portfolio.positions.keys()):
        check_stop_loss(context, stock)
    
    # ================= 3. 基础选股池 =================
    all_stocks = list(get_all_securities(['stock']).index)
    pool = filter_basic_stocks(context, all_stocks)
    
    # ================= 4. 市值筛选 =================
    pool = filter_by_market_cap(pool)
    
    if not pool:
        print("市值筛选后无股票")
        return
    
    # ================= 5. 基本面筛选 =================
    q = query(
        valuation.code
    ).filter(
        valuation.code.in_(pool),
        indicator.roe > g.roe_threshold,
        indicator.roa > g.roa_threshold
    )
    
    df_fund = get_fundamentals(q)
    target_pool = list(df_fund['code'])
    
    if not target_pool:
        print("基本面筛选后无股票")
        return
    
    # ================= 6. 动量计算（30日窗口） =================
    hist_prices = history(g.momentum_window, '1d', 'close', target_pool)
    
    momentum_dict = {}
    for stock in target_pool:
        hist_series = hist_prices[stock].dropna()
        if len(hist_series) >= g.momentum_window:
            ret = (hist_series.iloc[-1] - hist_series.iloc[0]) / hist_series.iloc[0]
            momentum_dict[stock] = ret
        else:
            momentum_dict[stock] = -999
    
    sorted_stocks = sorted(momentum_dict.items(), key=lambda item: item[1], reverse=True)
    buy_list = [stock for stock, momentum in sorted_stocks][:g.stock_num]
    
    if not buy_list:
        print("动量筛选后无股票")
        return
    
    print(f"最终选股({len(buy_list)}只): {buy_list[:3]}...")
    
    # ================= 7. 执行调仓 =================
    # 卖出不在买入列表中的股票
    for stock in context.portfolio.positions:
        if stock not in buy_list:
            position = context.portfolio.positions[stock]
            if position.total_amount > 0:
                order_target_value(stock, 0)
    
    # 等权重买入
    if len(buy_list) > 0:
        target_value = context.portfolio.total_value / len(buy_list)
        for stock in buy_list:
            order_target_value(stock, target_value)