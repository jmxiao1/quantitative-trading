# -*- coding: utf-8 -*-
"""聚宽策略编辑器可直接粘贴。书中月频 FF3 的可审计近似复现。
因子研究：六组市值加权、月末形成、下月收盘到收盘收益；不模拟融券。
账户交易：HML 的多头端（SH/BH 各半），不是 FF3 alpha 选股。
"""
from jqdata import *
import datetime as dt
import io
import numpy as np
import pandas as pd

MIN_LIST_DAYS = 365
TRIM_QUANTILE = 0.01  # 市值、BM 各剔除两端1%；置0作稳健性比较
MAX_PER_LEG = 30      # 实盘多头端每个规模档最多30只；None为完整两组
INVEST_RATIO = 0.98
ENABLE_TRADING = True
RF_FILE = ''         # 可选聚宽研究文件：month,rf；月份YYYY-MM，rf为月简单收益小数
RF_ANNUAL = 0.0      # 无文件时的显式假设！默认MKT=RM，不是假装取得历史无风险利率
PREFIX = 'ff3_book'
BATCH = 300
GROUPS = ('SL', 'SN', 'SH', 'BL', 'BN', 'BH')


def initialize(context):
    set_benchmark('000300.XSHG')  # 仅账户显示基准；MKT不使用沪深300替代
    set_option('use_real_price', True)
    set_option('avoid_future_data', True)
    set_slippage(PriceRelatedSlippage(0.001))
    log.set_level('order', 'error')
    g.snapshot = None
    g.rows = []
    g.completed = set()
    g.target = {}
    g.trade_date = None
    g.rf = {}
    if RF_FILE:
        raw = read_file(RF_FILE)
        if isinstance(raw, bytes):
            raw = raw.decode('utf-8-sig')
        rf = pd.read_csv(io.StringIO(raw), dtype={'month': str})
        if rf['month'].duplicated().any():
            raise ValueError('无风险收益文件月份重复')
        g.rf = dict(zip(rf['month'], rf['rf'].astype(float)))
    run_monthly(prepare_month, 1, time='before_open', reference_security='000300.XSHG')
    run_daily(sell_orders, time='09:35', reference_security='000300.XSHG')
    run_daily(buy_orders, time='09:40', reference_security='000300.XSHG')
    run_daily(month_end, time='after_close', reference_security='000300.XSHG')
    log.info('FF3启动；RF来源=%s；因子CSV与账户净值含义不同' % (RF_FILE or '常数假设'))


def batches(items):
    items = list(items)
    for i in range(0, len(items), BATCH):
        yield items[i:i + BATCH]


def as_date(value):
    return pd.Timestamp(value).date()


def price_frame(codes, start, end, fields, fq):
    frames = []
    for part in batches(codes):
        data = get_price(part, start_date=str(start), end_date=str(end),
                         frequency='daily', fields=fields, skip_paused=False,
                         fq=fq, panel=False)
        if data is None or data.empty:
            raise ValueError('行情批次为空：%s..%s' % (start, end))
        if not {'time', 'code'}.issubset(data.columns):
            raise ValueError('需要聚宽支持panel=False，返回time/code长表')
        frames.append(data)
    if not frames:
        raise ValueError('空股票池')
    out = pd.concat(frames, ignore_index=True)
    out['date'] = pd.to_datetime(out['time']).dt.date
    if out.duplicated(['date', 'code']).any():
        raise ValueError('行情存在重复日期/代码')
    return out


def assign_groups(frame):
    """纯函数：独立排序。边界等于中位数归S，BM等于70%归N。"""
    out = frame.copy()
    size_cut = out['cap'].median()
    low, high = out['bm'].quantile([0.3, 0.7]).values
    out['group'] = np.where(out['cap'] <= size_cut, 'S', 'B')
    out['group'] += np.where(out['bm'] <= low, 'L', np.where(out['bm'] > high, 'H', 'N'))
    if set(out['group']) != set(GROUPS):
        raise ValueError('六组不完整，停止形成；检查样本量或分位点重复')
    out['weight'] = out['cap'] / out.groupby('group')['cap'].transform('sum')
    out['market_weight'] = out['cap'] / out['cap'].sum()
    out['size_cut'] = size_cut
    out['bm30'] = low
    out['bm70'] = high
    return out


def make_snapshot(date):
    # 使用历史在市股票，不能用今天的股票列表回看历史。
    universe = get_all_securities(types=['stock'], date=date)
    names = universe.index.to_series().astype(str)
    a_share = names.str.startswith(('000', '001', '002', '003', '300', '301', '600', '601', '603', '605'))
    old = pd.to_datetime(universe['start_date']).dt.date <= date - dt.timedelta(days=MIN_LIST_DAYS)
    codes = universe.index[a_share.values & old.values].tolist()
    data = []
    for part in batches(codes):
        q = query(valuation.code, valuation.market_cap,
                  balance.equities_parent_company_owners, balance.pubDate).filter(valuation.code.in_(part))
        f = get_fundamentals(q, date=str(date))  # date而不是statDate，使用当时可见财报
        if f is None or f.empty:
            raise ValueError('财务批次为空，停止形成')
        data.append(f)
    if not data:
        raise ValueError('无历史股票')
    f = pd.concat(data, ignore_index=True).set_index('code')
    if f.index.duplicated().any():
        raise ValueError('财务记录重复')
    f = f.rename(columns={'market_cap': 'cap', 'equities_parent_company_owners': 'equity'})
    f['bm'] = f['equity'] / (f['cap'] * 1e8)  # 市值亿元，权益元
    f = f.replace([np.inf, -np.inf], np.nan).dropna(subset=['cap', 'equity', 'bm', 'pubDate'])
    f = f[(f['cap'] > 0) & (f['equity'] > 0) & (pd.to_datetime(f['pubDate']).dt.date <= date)]
    st = get_extras('is_st', f.index.tolist(), start_date=str(date), end_date=str(date), df=True)
    if st is None or st.empty:
        raise ValueError('历史ST数据为空')
    is_st = st.iloc[-1].reindex(f.index)
    f = f[is_st.notna() & (is_st == False)]
    p = price_frame(f.index, date, date, ['close', 'high', 'low', 'high_limit', 'low_limit', 'paused'], None)
    p = p.set_index('code').reindex(f.index)
    valid = p[['close', 'high', 'low', 'high_limit', 'low_limit', 'paused']].notna().all(axis=1)
    one_price = (p['high'] - p['low']).abs() < 0.00001
    at_limit = (p['close'] >= p['high_limit'] - 0.001) | (p['close'] <= p['low_limit'] + 0.001)
    f = f[valid & (p['paused'] == 0) & ~(one_price & at_limit)]
    if TRIM_QUANTILE:
        # 两项断点均在同一个过滤后样本计算，非依次缩小样本。
        keep = pd.Series(True, index=f.index)
        for field in ('cap', 'bm'):
            lo, hi = f[field].quantile([TRIM_QUANTILE, 1 - TRIM_QUANTILE])
            keep &= f[field].between(lo, hi)
        f = f[keep]
    if len(f) < 60:
        raise ValueError('有效股票少于60只')
    f = assign_groups(f)
    f['formation_date'] = str(date)
    write_file(PREFIX + '_holdings_' + date.strftime('%Y%m%d') + '.csv', f.to_csv(index=True), append=False)
    log.info('形成日%s，有效%d只；六组%s' % (date, len(f), f.groupby('group').size().to_dict()))
    return {'date': date, 'frame': f}


def aggregate_month(snapshot, returns, rf):
    """不因未来收益缺失而删除股票、重配权重。受影响组合直接标NaN。"""
    f = snapshot.copy()
    f['ret'] = returns.reindex(f.index)
    row = {}
    for group in GROUPS:
        part = f[f['group'] == group]
        bad = ~np.isfinite(part['ret'])
        row[group + '_missing_weight'] = float(part.loc[bad, 'weight'].sum())
        row[group] = np.nan if bad.any() else float((part['weight'] * part['ret']).sum())
    row['RM'] = np.nan if (~np.isfinite(f['ret'])).any() else float((f['market_weight'] * f['ret']).sum())
    row['RF'] = rf
    row['MKT'] = row['RM'] - rf
    row['SMB'] = (row['SL'] + row['SN'] + row['SH'] - row['BL'] - row['BN'] - row['BH']) / 3.0
    row['HML'] = (row['SH'] + row['BH'] - row['SL'] - row['BL']) / 2.0
    row['HML_LONG'] = (row['SH'] + row['BH']) / 2.0
    # 避免 jqdata 通配导入覆盖 Python all；先转数值数组再归约。
    row['complete'] = int(np.isfinite([row[k] for k in ('MKT', 'SMB', 'HML')]).all())
    return row


def settle_month(end):
    if g.snapshot is None or end.strftime('%Y-%m') in g.completed:
        return
    start, f = g.snapshot['date'], g.snapshot['frame']
    if end <= start:
        return
    p = price_frame(f.index, start, end, ['close'], 'post')
    start_price = p[p['date'] == start].set_index('code')['close'].reindex(f.index)
    end_price = p[p['date'] == end].set_index('code')['close'].reindex(f.index)
    returns = end_price / start_price - 1.0
    returns[(start_price <= 0) | (end_price <= 0)] = np.nan
    # 退市后供应商可能仍填充旧价格；主动标缺失，等待终止收益资料，不以0替代。
    alive = set(get_all_securities(types=['stock'], date=end).index)
    returns.loc[[c for c in f.index if c not in alive]] = np.nan
    month = end.strftime('%Y-%m')
    rf = float(g.rf.get(month, np.nan)) if RF_FILE else (1 + RF_ANNUAL) ** (1 / 12.0) - 1
    if not np.isfinite(rf):
        log.warn('RF缺失：%s，MKT将留空' % month)
    row = aggregate_month(f, returns, rf)
    row.update(month=month, formation_date=str(start), end_date=str(end), n=len(f),
               rf_source=RF_FILE or 'constant_assumption', price_return='jq_post_adjusted_proxy')
    g.rows.append(row)
    write_file(PREFIX + '_monthly.csv', pd.DataFrame(g.rows).to_csv(index=False), append=False)
    g.completed.add(month)
    if row['complete']:
        record(FF3_MKT_pct=100 * row['MKT'], FF3_SMB_pct=100 * row['SMB'], FF3_HML_pct=100 * row['HML'])
    log.info('FF3月收益%s: MKT=%s SMB=%s HML=%s complete=%s' %
             (month, row['MKT'], row['SMB'], row['HML'], row['complete']))


def prepare_month(context):
    date = as_date(context.previous_date)
    # 自动要求上一交易日为上月，避免半月启动冒充完整月因子。
    if date.month == context.current_dt.month:
        return
    settle_month(date)  # 补结算，若月末已结算会去重
    g.snapshot = make_snapshot(date)
    f = g.snapshot['frame']
    target = {}
    for group in ('SH', 'BH'):
        leg = f[f['group'] == group].sort_values(['cap'], ascending=False)
        if MAX_PER_LEG is not None:
            leg = leg.head(MAX_PER_LEG)
        for code, weight in (leg['cap'] / leg['cap'].sum()).items():
            target[code] = float(weight) * 0.5 * INVEST_RATIO
    g.target = target
    g.trade_date = context.current_dt.date()
    tax = 0.0005 if g.trade_date >= dt.date(2023, 8, 28) else 0.001
    set_order_cost(OrderCost(open_tax=0, close_tax=tax, open_commission=0.0003,
                            close_commission=0.0003, min_commission=5), type='stock')


def sell_orders(context):
    if not ENABLE_TRADING or g.trade_date != context.current_dt.date():
        return
    data = get_current_data()
    nav = context.portfolio.total_value
    for code, pos in list(context.portfolio.positions.items()):
        target = g.target.get(code, 0) * nav
        q = data[code]
        if pos.value > target and not q.paused and q.last_price > q.low_limit:
            order_target_value(code, target)


def buy_orders(context):
    if not ENABLE_TRADING or g.trade_date != context.current_dt.date():
        return
    data = get_current_data()
    nav = context.portfolio.total_value
    for code, weight in sorted(g.target.items(), key=lambda x: -x[1]):
        q = data[code]
        if q.paused or q.is_st or '退' in q.name or not (q.low_limit < q.last_price < q.high_limit):
            continue
        pos = context.portfolio.positions.get(code)
        held = pos.value if pos else 0.0
        cash = context.portfolio.available_cash * 0.995
        amount = min(weight * nav - held, cash)
        if amount >= q.last_price * 100 + 5:
            order_target_value(code, held + amount)
    # 无法成交的目标本月不替换、不追单；下月再试，避免隐含日频再平衡。


def month_end(context):
    today = context.current_dt.date()
    # 未来交易日历不是未来行情，不查询明日价格或财报。
    following = get_trade_days(start_date=today + dt.timedelta(days=1), count=1)
    if len(following) and as_date(following[0]).month != today.month:
        settle_month(today)
