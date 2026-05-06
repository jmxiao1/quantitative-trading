# 导入聚宽函数库
from jqdata import *

def initialize(context):
    # 设定基准为中证500指数
    set_benchmark('000905.XSHG')
    set_option('use_real_price', True)
    
    # 设定手续费 (注意：场内货基通常免印花税，部分券商免佣金，这里采用保守的标准费率)
    set_order_cost(OrderCost(close_tax=0.001, open_commission=0.0003, close_commission=0.0003, min_commission=5), type='stock')
    
    # --- 策略核心参数 ---
    g.stock_num = 10           # 目标持仓数量
    g.index = '000300.XSHG'    # 择时基准：沪深 300
    g.money_fund = '511880.XSHG' # 避险资产：银华日利 (场内货币基金，近乎零回撤)
    g.ma_days = 60             # 择时均线周期
    
    # 财务阈值（保持之前的黄金平衡点）
    g.roe_threshold = 5.0
    g.roa_threshold = 3.0
    
    # 定期执行：每个月第一个交易日运行
    run_monthly(rebalance, monthday=1, time='09:30')

def check_market_timing(context):
    """
    择时模块：判断大盘趋势
    """
    hist = attribute_history(g.index, g.ma_days, '1d', ['close'])
    ma60 = hist['close'].mean()
    current_price = hist['close'][-1]
    return current_price > ma60

def filter_basic_stocks(context, stock_list):
    """
    基础排雷：剔除停牌、ST、次新股
    """
    current_data = get_current_data()
    stock_list = [stock for stock in stock_list if not current_data[stock].paused and not current_data[stock].is_st]
    stock_list = [stock for stock in stock_list if (context.current_dt.date() - get_security_info(stock).start_date).days > 250]
    return stock_list

def rebalance(context):
    """
    核心调仓逻辑：股基轮动执行层
    """
    # 1. 宏观风控判断
    is_safe = check_market_timing(context)
    
    # ================= 分支 A：市场不安全 -> 切换至货币基金 =================
    if not is_safe:
        print(f"{context.current_dt.date()}: 大盘走弱，执行【股票清仓，买入货基】避险。")
        # 清空所有股票持仓
        for stock in context.portfolio.positions:
            if stock != g.money_fund:
                order_target_value(stock, 0)
        
        # 将全部资金买入货币基金吃利息
        order_target_value(g.money_fund, context.portfolio.total_value)
        return

    # ================= 分支 B：市场安全 -> 切换至小市值股票 =================
    print(f"{context.current_dt.date()}: 大盘安全，执行【货基清仓，买入股票】进攻。")
    
    # 如果持有货基，先清空货基仓位释放资金
    if g.money_fund in context.portfolio.positions:
        order_target_value(g.money_fund, 0)

    # 选股流程
    all_stocks = list(get_all_securities(['stock']).index)
    pool = filter_basic_stocks(context, all_stocks)
    
    # 财务选股 + 小市值排序
    q = query(
        valuation.code,
        valuation.market_cap
    ).filter(
        valuation.code.in_(pool),
        indicator.roe > g.roe_threshold,
        indicator.roa > g.roa_threshold
    ).order_by(
        valuation.market_cap.asc()
    ).limit(g.stock_num)
    
    df = get_fundamentals(q)
    buy_list = list(df['code'])
    
    # 卖出不在目标池的股票
    for stock in context.portfolio.positions:
        if stock not in buy_list and stock != g.money_fund:
            order_target_value(stock, 0)
            
    # 等权重买入绩优小盘股
    if len(buy_list) > 0:
        target_value = context.portfolio.total_value / len(buy_list)
        for stock in buy_list:
            order_target_value(stock, target_value)