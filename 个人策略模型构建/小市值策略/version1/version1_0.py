# 导入聚宽函数库
from jqdata import *

def initialize(context):
    # 设定基准为中证500指数
    set_benchmark('000905.XSHG')
    set_option('use_real_price', True)
    set_order_cost(OrderCost(close_tax=0.001, open_commission=0.0003, close_commission=0.0003, min_commission=5), type='stock')
    
    # 策略核心参数设定
    g.stock_num = 10           # 目标持仓数量
    g.index = '000300.XSHG'    # 宏观择时基准：沪深300
    g.ma_days = 60             # 择时均线周期
    
    # 定期执行：每个月第一个交易日的 09:30 执行调仓
    run_monthly(rebalance, monthday=1, time='09:30')

def check_market_timing(context):
    """
    宏观风控模块：判断大盘是否处于下降通道
    """
    # 获取沪深300过去 60 天的收盘价
    hist = attribute_history(g.index, g.ma_days, '1d', ['close'])
    ma60 = hist['close'].mean()
    current_price = hist['close'][-1]
    
    # 如果当前价格在 60 日均线之上，判定为安全（返回 True）
    return current_price > ma60

def filter_basic_stocks(context, stock_list):
    """
    基础排雷过滤
    """
    current_data = get_current_data()
    # 剔除停牌、ST、*ST
    stock_list = [stock for stock in stock_list if not current_data[stock].paused and not current_data[stock].is_st]
    # 剔除上市不足一年的次新股
    stock_list = [stock for stock in stock_list if (context.current_dt.date() - get_security_info(stock).start_date).days > 250]
    return stock_list

def rebalance(context):
    """
    核心调仓逻辑
    """
    # ================= 1. 宏观风控拦截 =================
    is_safe = check_market_timing(context)
    
    if not is_safe:
        # 大盘破位，执行无条件清仓防守
        for stock in context.portfolio.positions:
            order_target_value(stock, 0)
        print(f"{context.current_dt.date()}: 大盘跌破{g.ma_days}日均线，空仓防守避险。")
        return # 直接结束本次调仓，不再买入
        
    # ================= 2. 安全期选股逻辑 =================
    all_stocks = list(get_all_securities(['stock']).index)
    pool = filter_basic_stocks(context, all_stocks)
    
    # 财务与市值初筛：只要求盈利 (ROE>0)，按市值排序取前100进入动量池
    q = query(
        valuation.code,
        valuation.market_cap
    ).filter(
        valuation.code.in_(pool),
        indicator.roe > 5,
        indicator.roa > 0# 动态弹性：只要正收益，剔除财务黑洞
    ).order_by(
        valuation.market_cap.asc()
    ).limit(
        100 
    )
    df = get_fundamentals(q)
    target_pool = list(df['code'])
    
    # ================= 3. 动量趋势过滤 =================
    # 获取这 100 只股票过去 20 天的收盘价
    hist_prices = history(20, '1d', 'close', target_pool)
    momentum_stocks = []
    
    for stock in target_pool:
        # 计算 20 日收益率
        ret_20d = (hist_prices[stock][-1] - hist_prices[stock][0]) / hist_prices[stock][0]
        # 剔除近期暴跌（跌幅超过 5%）的股票，不接飞刀
        if ret_20d > -0.05:
            momentum_stocks.append(stock)
            
    # ================= 4. 最终调仓执行 =================
    buy_list = momentum_stocks[:g.stock_num]
    
    # 卖出不在目标池的股票
    for stock in context.portfolio.positions:
        if stock not in buy_list:
            order_target_value(stock, 0)
            
    # 等权重买入
    if len(buy_list) > 0:
        target_value = context.portfolio.total_value / len(buy_list)
        for stock in buy_list:
            order_target_value(stock, target_value)