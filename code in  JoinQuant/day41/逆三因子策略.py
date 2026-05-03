# 导入聚宽函数库
from jqdata import *
import pandas as pd

# 初始化函数，设定基准等等
def initialize(context):
    # 设定基准为沪深300指数
    set_benchmark('000300.XSHG')
    # 开启动态复权模式(真实价格)
    set_option('use_real_price', True)
    # 输出内容到日志 log.info()
    log.info('初始函数开始运行且全局只运行一次')
    
    # 设定系统提示及滑点（此处设定滑点为固定值0.02元）
    set_slippage(FixedSlippage(0.02))
    # 设定手续费：买入万三，卖出万三加千一印花税，最低交割费5元
    set_order_cost(OrderCost(close_tax=0.001, open_commission=0.0003, close_commission=0.0003, min_commission=5), type='stock')

    # ========== 策略参数设定 ==========
    # 目标持仓数量
    g.stock_num = 10 
    # 基础股票池：中证800（000906.XSHG）包含了沪深300和中证500，覆盖全面
    g.index_code = '000906.XSHG'

    # 按月运行，每月第一个交易日 09:30 执行调仓 rebalance 函数
    run_monthly(rebalance, monthday=1, time='09:30')

# 过滤停牌和ST股票的辅助函数
def filter_paused_and_st(stock_list):
    current_data = get_current_data()
    # 过滤停牌
    stock_list = [stock for stock in stock_list if not current_data[stock].paused]
    # 过滤ST、*ST、退市股
    stock_list = [stock for stock in stock_list if not current_data[stock].is_st]
    return stock_list

# 定时触发的调仓函数
def rebalance(context):
    log.info('开始执行月度调仓')
    
    # 1. 获取基础股票池
    pool = get_index_stocks(g.index_code)
    # 过滤停牌和ST股票
    pool = filter_paused_and_st(pool)

    if len(pool) == 0:
        return
        
    # 2. 查询财务数据
    # valuation.market_cap: 总市值
    # valuation.pb_ratio: 市净率（PB）
    q = query(
        valuation.code,
        valuation.market_cap,
        valuation.pb_ratio
    ).filter(
        valuation.code.in_(pool)
    )
    
    # 获取基本面数据，返回 Pandas DataFrame
    df = get_fundamentals(q)
    
    # 如果没取到数据则跳过
    if df.empty:
        return

    # 3. 计算因子排名 (核心：逆三因子逻辑)
    # 逆市值因子：倾向大盘股，按市值降序排（市值越大，rank排名数值越小）
    df['cap_rank'] = df['market_cap'].rank(ascending=False)
    
    # 逆价值因子：倾向高估值/成长股（低账面市值比 = 高PB），按PB降序排
    df['pb_rank'] = df['pb_ratio'].rank(ascending=False)
    
    # 计算总得分 (此处按 1:1 等权相加，您也可以给 cap_rank 和 pb_rank 分配不同权重)
    df['total_score'] = df['cap_rank'] + df['pb_rank']
    
    # 按总得分升序排列（排名数字越小意味着双指标综合越靠前）
    df = df.sort_values(by='total_score', ascending=True)
    
    # 截取排名前 g.stock_num 的股票代码列表
    target_list = list(df['code'])[:g.stock_num]
    
    log.info(f"本月目标选股: {target_list}")

    # 4. 执行交易调仓
    # 获取当前真实持仓的股票代码列表
    current_holdings = list(context.portfolio.positions.keys())
    
    # 卖出：如果当前持仓股不在新的目标列表中，则平仓
    for stock in current_holdings:
        if stock not in target_list:
            order_target(stock, 0)
            log.info(f"卖出不在目标池的股票: {stock}")

    # 买入/调仓：对目标列表中的股票进行等权重分配资金
    if len(target_list) > 0:
        # 每只股票的目标权重
        target_weight = 1.0 / len(target_list)
        
        for stock in target_list:
            # order_target_percent 自动根据总资产分配比例，买入或调整仓位
            order_target_percent(stock, target_weight)
            log.info(f"调整股票仓位至目标比例: {stock}, 权重: {target_weight*100}%")