
"""
================================================================================
 DHS三因子模型选股策略（聚宽 JoinQuant 版）
================================================================================
一、理论来源
    DHS 模型：Daniel, Hirshleifer & Subrahmanyam (1998) 行为金融经典模型。
    模型假设"有信息投资者"存在两类系统性心理偏差：
        1) 过度自信(Overconfidence)：高估私有信息的精度，导致过度交易、
           过度反应、放大价格波动；
        2) 有偏自我归因(Biased Self-Attribution)：盈利归功自己、亏损归咎
           外部，导致动量漂移与长期反转。
    由该模型可推导出三个可交易的选股因子（即本策略的"DHS三因子"）：

    【因子1 · 反转因子】过度反应 → 短期价格超调后向基本面回归
        度量：过去20个交易日收益率，越低（越超跌）越好
    【因子2 · 换手率因子】过度自信 → 过度交易，高换手 = 过度追捧 = 高估
        度量：过去20日平均换手率，越低越好
    【因子3 · 波动率因子】过度自信交易放大波动（DHS推论：市场波动高于
        基本面波动）→ 低波动股未来跑赢
        度量：过去60日日收益率标准差，越低越好
    【可选 · 动量因子】有偏自我归因 → 动量效应（A股个股动量长期偏弱，
        默认权重为0；若你的资料将"DHS三因子"定义为 动量+反转+换手率，
        把 WEIGHT_MOMENTUM 改为 1.0、WEIGHT_VOLATILITY 改为 0 即可）

二、策略逻辑
    1) 月度调仓：每月第一个交易日 9:30 ——
       股票池：全市场 → 剔除 ST/*ST/退市/停牌/次新股/科创板/北交所/亏损股，
       （可选）仅保留总市值最小的 POOL_SIZE 只（小市值增强，收益主引擎）；
       计算三因子，各自升序排名（排名1=最优），按权重合成综合得分；
       等权买入综合得分最小的 HOLD_NUM 只股票。
    2) 风格择时（默认关闭，经对照证伪）：闸门类风控会滤掉本策略的主要
       超额收益，代码保留仅供复测；
    3) 急跌熔断（USE_CRASH_BREAKER，默认关闭）：仅当组合5日累计跌幅超过
       CRASH_5D_DROP 时降至 CRASH_OFF_RATIO 仓位并锁定 CRASH_LOCK_DAYS 个
       交易日，平时零干预，不干预常规行情。

三、风险提示
    回测收益不代表未来表现。小市值风格在 2024 年 1-2 月与 2026 年上半年
    均出现过剧烈回撤；择时只能缓解、无法消除风格风险，压力测试时可用
    MIN_MARKET_CAP 避开微盘壳股，并做参数邻域检验。
    使用方法：聚宽 -> 我的策略 -> 新建策略 -> 粘贴本文件全部代码 ->
    回测频率选"天"，起始日期建议选某月1日（如 2018-01-01）。
================================================================================
"""

from jqdata import *
import pandas as pd
import numpy as np


# ================================ 可调参数 ================================
HOLD_NUM       = 20     # 持仓数量（等权）；想更激进可降到 10
POOL_SIZE      = 1000   # 股票池：总市值最小的N只；设为 None 则全市场（更稳但收益降低）
MIN_LIST_DAYS  = 120    # 剔除上市不足N个自然日的次新股
MIN_AVG_MONEY  = 2e7    # 剔除20日日均成交额低于2000万元的股票
MIN_MARKET_CAP = 0      # 最小总市值（亿元）：A组对照显示20亿下限收益腰斩而回撤仅降4pp，回退
EXCLUDE_LOSS   = True   # 剔除亏损股（市盈率<=0），避开容易崩盘的无盈利微盘股

# 三因子权重（各因子升序排名后加权求和，综合得分越小越好）
WEIGHT_REVERSAL   = 1.0   # 反转因子
WEIGHT_TURNOVER   = 1.0   # 换手率因子
WEIGHT_VOLATILITY = 1.0   # 波动率因子
WEIGHT_MOMENTUM   = 0.0   # 动量因子（可选，默认关闭）

USE_INDEX_TIMING = False          # 风格择时：经四组对照证伪（闸门滤掉alpha），默认关闭，代码保留可复测
TIMING_INDEX     = '399303.XSHE'  # 择时指数：国证2000（与持仓同风格；备选'000852.XSHG'中证1000）
TIMING_MA        = 200            # 择时均线窗口，可对比测试 120 / 250
POSITION_AT_RISK_OFF = 0.5        # 风险off时的仓位比例（0=清仓避险，0.5=半仓防御）

# 急跌熔断：只在组合短期急跌时降仓，平时零干预（与趋势闸门机制不同）
USE_CRASH_BREAKER = False         # 急跌熔断开关
CRASH_5D_DROP     = -0.12         # 组合5日累计跌幅达到该值触发
CRASH_OFF_RATIO   = 0.3           # 触发后降至的仓位比例
CRASH_LOCK_DAYS   = 15            # 触发后维持低仓的交易日数


# ================================ 策略框架 ================================
def initialize(context):
    set_benchmark('000905.XSHG')                 # 基准：中证500
    set_option('use_real_price', True)           # 按真实价格撮合
    set_option('avoid_future_data', True)        # 禁止使用未来数据
    set_slippage(PriceRelatedSlippage(0.002))    # 双边0.2%滑点
    set_order_cost(OrderCost(open_tax=0, close_tax=0.001,      # 印花税(卖出)
                             open_commission=0.0003,           # 佣金万3
                             close_commission=0.0003,
                             min_commission=5), type='stock')
    g.timed_out = False   # 择时状态：True=避险降仓中
    g.breaker_on = False  # 熔断状态
    g.breaker_left = 0    # 熔断剩余锁定交易日
    g.value_hist = []     # 近6日组合总资产（熔断观测窗口）
    # 每月第1个交易日开盘调仓
    run_monthly(rebalance, 1, time='9:30', reference_security='000300.XSHG')
    # 每日大盘择时检查（USE_INDEX_TIMING=False 时自动跳过）
    run_daily(index_timing_check, time='9:31', reference_security='000300.XSHG')
    # 每日急跌熔断检查（USE_CRASH_BREAKER=False 时自动跳过）
    run_daily(crash_breaker_check, time='9:32', reference_security='000300.XSHG')
    log.set_level('order', 'error')
    log.info('DHS三因子策略启动：反转 + 换手率 + 波动率（等权合成）')


# ------------------------------- 大盘择时 --------------------------------
def market_trend_ok(context):
    """TIMING_INDEX 上一交易日收盘价 >= TIMING_MA 日均线视为多头；
    指数数据异常时默认多头（退化为无择时，绝不误判成空仓）"""
    try:
        closes = get_price(TIMING_INDEX, count=TIMING_MA, end_date=context.previous_date,
                           frequency='daily', fields=['close'])['close']
        if len(closes) < TIMING_MA:
            return True
        return closes.iloc[-1] >= closes.mean()
    except Exception:
        return True


def index_timing_check(context):
    """每日检查：跌破均线降至防御仓位；收复均线后次日自动恢复满仓"""
    if not USE_INDEX_TIMING:
        return
    if not market_trend_ok(context):
        if not g.timed_out:
            g.timed_out = True
            log.info('跌破%d日均线，降至防御仓位%.0f%%' % (TIMING_MA, POSITION_AT_RISK_OFF * 100))
            def_weight = context.portfolio.total_value * POSITION_AT_RISK_OFF / HOLD_NUM
            for s in list(context.portfolio.positions):
                if POSITION_AT_RISK_OFF <= 0 or \
                        context.portfolio.positions[s].value > def_weight:
                    order_target_value(s, def_weight)
    elif g.timed_out:
        g.timed_out = False
        log.info('收复%d日均线，恢复满仓' % TIMING_MA)
        rebalance(context)


def crash_breaker_check(context):
    """急跌熔断：组合5日累计跌幅超阈值→降至低仓并锁定N个交易日；平时零干预"""
    if not USE_CRASH_BREAKER:
        return
    value = context.portfolio.total_value
    g.value_hist.append(value)
    if len(g.value_hist) > 6:
        g.value_hist.pop(0)
    if g.breaker_on:
        g.breaker_left -= 1
        if g.breaker_left <= 0:
            g.breaker_on = False
            g.value_hist = []       # 重置观测窗口，避免立刻重复触发
            log.info('熔断结束，恢复常态')
            rebalance(context)
        return
    if len(g.value_hist) == 6 and g.value_hist[0] > 0:
        drop = value / g.value_hist[0] - 1
        if drop <= CRASH_5D_DROP:
            g.breaker_on = True
            g.breaker_left = CRASH_LOCK_DAYS
            log.info('组合5日跌幅%.1f%%，熔断降至%.0f%%仓位' % (drop * 100, CRASH_OFF_RATIO * 100))
            def_weight = context.portfolio.total_value * CRASH_OFF_RATIO / HOLD_NUM
            for s in list(context.portfolio.positions):
                if context.portfolio.positions[s].value > def_weight:
                    order_target_value(s, def_weight)


# ------------------------------ 股票池构建 -------------------------------
def build_pool(context):
    prev = context.previous_date
    secs = get_all_securities(['stock'], prev)

    # 1) 剔除次新股（start_date 可能是 date 对象或 datetime64，统一转时间戳再相减）
    listed_days = (pd.Timestamp(prev) - pd.to_datetime(secs['start_date'])).dt.days
    secs = secs[listed_days >= MIN_LIST_DAYS]
    codes = list(secs.index)

    # 2) 剔除科创板/北交所/新三板
    codes = [c for c in codes
             if c[:3] not in ('688', '689') and c[0] not in ('4', '8')]

    # 3) 剔除 ST/*ST/退市整理/当前停牌
    cur = get_current_data()
    codes = [c for c in codes
             if (not cur[c].paused) and (not cur[c].is_st)
             and ('ST' not in cur[c].name.upper()) and ('退' not in cur[c].name)]

    # 4) 市值过滤（小市值增强），并取流通市值用于换手率计算
    fund = get_fundamentals(
        query(valuation.code, valuation.market_cap, valuation.circulating_market_cap,
              valuation.pe_ratio)
        .filter(valuation.code.in_(codes)), date=prev)
    fund = fund[fund['market_cap'] >= MIN_MARKET_CAP]
    if EXCLUDE_LOSS:
        fund = fund[fund['pe_ratio'] > 0]   # 剔除亏损/无盈利数据股
    if POOL_SIZE:
        fund = fund.sort_values('market_cap').head(POOL_SIZE)
    return list(fund['code']), dict(zip(fund['code'], fund['circulating_market_cap']))


# ------------------------------- 因子打分 --------------------------------
def compute_targets(context, codes, circ_mv):
    # history 取截至上一交易日的日线数据，无未来函数
    close  = history(61, '1d', 'close',  codes, df=True)
    volume = history(21, '1d', 'volume', codes, df=True)
    money  = history(21, '1d', 'money',  codes, df=True)

    df = pd.DataFrame(index=codes)
    # 因子1 反转：20日收益率（越低越好）
    df['reversal'] = close.iloc[-1] / close.iloc[-21] - 1
    # 因子2 换手率：日均成交量 / 流通股本（越低越好）
    mv = pd.Series(circ_mv)                        # 流通市值（亿元）
    shares = mv * 1e8 / close.iloc[-1]             # 流通股本估算
    df['turnover'] = volume.mean() / shares
    # 因子3 波动率：60日日收益率标准差（越低越好）
    df['volatility'] = close.pct_change().std()
    # 可选因子 动量：60日前 -> 20日前的区间收益（越高越好）
    df['momentum'] = close.iloc[-21] / close.iloc[0] - 1

    # 流动性/交易状态过滤：日均成交额达标 + 近20日至少15天正常交易
    df = df[(money.mean() >= MIN_AVG_MONEY) & ((volume > 0).sum() >= 15)]
    df = df.dropna()

    # 各因子升序排名（动量为降序），加权合成综合得分，取最小的 HOLD_NUM 只
    score = (WEIGHT_REVERSAL     * df['reversal'].rank(ascending=True)
             + WEIGHT_TURNOVER   * df['turnover'].rank(ascending=True)
             + WEIGHT_VOLATILITY * df['volatility'].rank(ascending=True)
             + WEIGHT_MOMENTUM   * df['momentum'].rank(ascending=False))
    return score.nsmallest(HOLD_NUM)


# ------------------------------- 月度调仓 --------------------------------
def rebalance(context):
    risk_on = (not USE_INDEX_TIMING) or market_trend_ok(context)
    if USE_INDEX_TIMING and not risk_on:
        g.timed_out = True          # 标记避险状态，恢复满仓由每日检查函数触发
    ratio = 1.0 if risk_on else POSITION_AT_RISK_OFF
    if g.breaker_on:                # 熔断期间月度调仓也维持低仓
        ratio = min(ratio, CRASH_OFF_RATIO)
    if ratio <= 0:
        for s in list(context.portfolio.positions):
            order_target(s, 0)
        return

    codes, circ_mv = build_pool(context)
    if len(codes) < HOLD_NUM:
        log.info('股票池不足 %d 只，本月跳空调仓' % HOLD_NUM)
        return
    targets = compute_targets(context, codes, circ_mv)

    cur = get_current_data()
    # 先卖：不在目标池的持仓（停牌/跌停卖不掉的自动保留，下月再处理）
    for s in list(context.portfolio.positions):
        if s in targets.index:
            continue
        if cur[s].paused or cur[s].last_price <= cur[s].low_limit * 1.005:
            log.info('暂无法卖出（停牌/跌停）：%s %s' % (s, cur[s].name))
            continue
        order_target(s, 0)

    # 防御模式下：已持有的目标股缩到防御权重（只减仓，卖出不受手数限制）
    if ratio < 1.0:
        def_weight = context.portfolio.total_value * ratio / HOLD_NUM
        for c in targets.index:
            if c in context.portfolio.positions and \
                    context.portfolio.positions[c].value > def_weight * 1.05:
                order_target_value(c, def_weight)

    # 后买：等权买入目标股，单笔目标 = 总资产 * 仓位比例 / HOLD_NUM。
    # 已持有的不再补单（避免差额不足100股的碎单被拒）；
    # 停牌/一字涨停开盘的跳过；单笔金额买不起1手的高价股跳过。
    held = set(context.portfolio.positions)
    buy_list = [c for c in targets.index
                if (not cur[c].paused)
                and cur[c].day_open < cur[c].high_limit * 0.995
                and c not in held]
    if not buy_list:
        return
    weight = context.portfolio.total_value * ratio / HOLD_NUM
    buy_list = [c for c in buy_list if cur[c].last_price * 100 <= weight]
    for c in buy_list:
        order_target_value(c, weight)

    names = [get_security_info(c).display_name for c in buy_list[:5]]
    log.info('本月建仓 %d 只 | 前5：%s' % (len(buy_list), '、'.join(names)))
