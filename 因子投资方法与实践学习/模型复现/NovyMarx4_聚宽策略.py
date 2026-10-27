"""Novy-Marx四因子的A股月度近似实现；独立聚宽策略。
MKT + HML_NM + MOM_NM + PMU；包含特征行业去均值及收益行业对冲。
"""
from jqdata import *
import datetime as dt
import io
import numpy as np
import pandas as pd

PREFIX = 'novymarx4_book'
BATCH = 300
MIN_LIST_DAYS = 365
MIN_INDUSTRY_SIZE = 5
INVEST_RATIO = .98
MAX_PER_LEG = 20
ENABLE_TRADING = True
TRADE_MODE = 'ALL_LONG'  # ALL_LONG / VALUE_LONG / MOM_LONG / PROFIT_LONG
RF_FILE = ''  # month,rf；月收益小数
RF_ANNUAL = 0.0
SORT_LOW, SORT_HIGH = .3, .7  # 本地化HML式30/70断点，可做1/3、2/3敏感性比较
FACTORS = ('HML_NM', 'MOM_NM', 'PMU')
GROUPS = ('SL', 'SN', 'SH', 'BL', 'BN', 'BH')


def initialize(context):
    if TRADE_MODE not in ('ALL_LONG', 'VALUE_LONG', 'MOM_LONG', 'PROFIT_LONG'):
        raise ValueError('未知交易模式')
    set_benchmark('000300.XSHG')
    set_option('use_real_price', True)
    set_option('avoid_future_data', True)
    set_slippage(PriceRelatedSlippage(.001))
    log.set_level('order', 'error')
    g.snapshot, g.rows, g.completed = None, [], set()
    g.target, g.trade_date, g.rf = {}, None, {}
    if RF_FILE:
        raw = read_file(RF_FILE)
        if isinstance(raw, bytes):
            raw = raw.decode('utf-8-sig')
        rf = pd.read_csv(io.StringIO(raw), dtype={'month': str})
        if rf['month'].duplicated().any():
            raise ValueError('RF月份重复')
        g.rf = dict(zip(rf['month'], rf['rf'].astype(float)))
    run_monthly(prepare_month, 1, time='before_open', reference_security='000300.XSHG')
    run_daily(sell_orders, time='09:35', reference_security='000300.XSHG')
    run_daily(buy_orders, time='09:40', reference_security='000300.XSHG')
    run_daily(month_end, time='after_close', reference_security='000300.XSHG')
    log.info('NM4 A股月度近似版：RF=%s；行业收益为样本内代理' % (RF_FILE or '常数假设'))


def accounting_year(date):
    # 六月末及以后采用上年年报；此前采用上上年年报。
    return date.year - (1 if date.month >= 6 else 2)


def validate_accounts(inc, bal, year, date, watch_date_filtered=False):
    """显式校验两表报告期与公告日；不能识别供应商覆盖历史的重述版本。"""
    f = inc.join(bal, how='inner')
    expected = dt.date(year, 12, 31)
    ok = pd.Series(True, index=f.index)
    for prefix in ('i', 'b'):
        pub = pd.to_datetime(f[prefix + '_pub'], errors='coerce').dt.date
        stat = pd.to_datetime(f[prefix + '_stat'], errors='coerce').dt.date
        # 历史接口用watch_date约束披露时点；未返回公告日时保留NaT，不伪造日期。
        known = pub.notna() & (pub <= date)
        if watch_date_filtered:
            known |= pub.isna()
        ok &= known & (stat == expected)
    f['gpa'] = (f['revenue'] - f['cost']) / f['assets']
    ok &= (f['assets'] > 0) & (f['equity'] > 0)
    ok &= np.isfinite(f[['revenue', 'cost', 'assets', 'equity', 'gpa']]).all(axis=1)
    return f.loc[ok].copy()  # 允许负毛利，不删除低盈利空头候选


def annual_accounts(codes, date):
    year = accounting_year(date)
    rows = []
    for part in batches(codes):
        # 防未来模式支持观察日期；年度流量不能改成最近一季或Q4单季。
        h = get_history_fundamentals(part,
                fields=[income.operating_revenue, income.operating_cost,
                        balance.total_assets, balance.equities_parent_company_owners],
                watch_date=str(date), count=3, interval='1y', stat_by_year=True)
        if h is None:
            raise ValueError('年报接口返回空对象')
        rows.append(h)
    if not rows:
        raise ValueError('空年报股票池')
    h = pd.concat(rows, ignore_index=True)
    required = {'code', 'statDate', 'operating_revenue', 'operating_cost',
                'total_assets', 'equities_parent_company_owners'}
    if not required.issubset(h.columns):
        raise ValueError('年报字段缺失：' + str(sorted(required - set(h.columns))))
    h['statDate'] = pd.to_datetime(h['statDate'], errors='raise')
    if h['statDate'].isna().any() or (h['statDate'] > pd.Timestamp(date)).any():
        raise ValueError('年报报告期为空或在未来')
    if h.duplicated(['code', 'statDate']).any():
        raise ValueError('年报报告期重复，不能任意选取修订版')
    h = h[h['statDate'] == pd.Timestamp(year, 12, 31)].copy()
    if 'pubDate' not in h.columns:
        h['pubDate'] = pd.NaT
    h = h.set_index('code')
    inc = h[['statDate', 'pubDate', 'operating_revenue', 'operating_cost']].rename(
        columns={'statDate': 'i_stat', 'pubDate': 'i_pub',
                 'operating_revenue': 'revenue', 'operating_cost': 'cost'})
    bal = h[['statDate', 'pubDate', 'total_assets', 'equities_parent_company_owners']].rename(
        columns={'statDate': 'b_stat', 'pubDate': 'b_pub',
                 'total_assets': 'assets', 'equities_parent_company_owners': 'equity'})
    return validate_accounts(inc, bal, year, date, watch_date_filtered=True)


def build_groups(frame):
    f = frame.copy()
    f = f.replace([np.inf, -np.inf], np.nan).dropna(subset=['cap', 'bm', 'gpa', 'mom', 'industry'])
    f = f[(f.cap > 0) & (f.bm > 0)]
    f = f[f.groupby('industry')['cap'].transform('size') >= MIN_INDUSTRY_SIZE].copy()
    if len(f) < 60:
        raise ValueError('有效共同样本不足60只')
    f['logbm'] = np.log(f.bm)
    f['market_weight'] = f.cap / f.cap.sum()
    f['industry_weight'] = f.cap / f.groupby('industry').cap.transform('sum')
    size_cut = f.cap.median()
    for factor, signal in [('HML_NM', 'logbm'), ('MOM_NM', 'mom'), ('PMU', 'gpa')]:
        # 明确采用样本内等权特征均值；收益行业组合另用市值权重。
        f[factor + '_signal'] = f[signal] - f.groupby('industry')[signal].transform('mean')
        lo, hi = f[factor + '_signal'].quantile([SORT_LOW, SORT_HIGH])
        labels = pd.Series(np.where(f.cap <= size_cut, 'S', 'B'), index=f.index)
        labels += np.where(f[factor + '_signal'] <= lo, 'L', np.where(f[factor + '_signal'] > hi, 'H', 'N'))
        if set(labels) != set(GROUPS):
            raise ValueError(factor + '六组不完整')
        f[factor + '_group'] = labels
        f[factor + '_weight'] = f.cap / f.cap.groupby(labels).transform('sum')
        f[factor + '_low_cut'], f[factor + '_high_cut'] = lo, hi
    f['size_cut'] = size_cut
    return f


def make_snapshot(date):
    universe = get_all_securities(types=['stock'], date=date)
    names = universe.index.to_series().astype(str)
    allowed = names.str.startswith(('000', '001', '002', '003', '300', '301', '600', '601', '603', '605'))
    old = pd.to_datetime(universe.start_date).dt.date <= date - dt.timedelta(days=MIN_LIST_DAYS)
    codes = universe.index[allowed.values & old.values].tolist()
    if not codes:
        raise ValueError('股票池为空')
    rows, industries = [], {}
    for part in batches(codes):
        q = query(valuation.code, valuation.market_cap).filter(valuation.code.in_(part))
        rows.append(get_fundamentals(q, date=str(date)))
        data = get_industry(part, date=str(date))
        for code in part:
            industries[code] = data.get(code, {}).get('sw_l1', {}).get('industry_code')
    f = pd.concat(rows, ignore_index=True).set_index('code').rename(columns={'market_cap': 'cap'})
    if f.index.duplicated().any():
        raise ValueError('市值重复')
    f['industry'] = pd.Series(industries)
    # 银行/非银金融的营业成本定义缺乏可比性，本地化版本显式排除。
    f = f[f.industry.notna() & ~f.industry.isin(['801780', '801790'])]
    f = f.join(annual_accounts(f.index, date), how='inner')
    f['bm'] = f.equity / (f.cap * 1e8)
    st = get_extras('is_st', f.index.tolist(), start_date=str(date), end_date=str(date), df=True)
    if st is None or st.empty:
        raise ValueError('历史ST数据缺失')
    status = st.iloc[-1].reindex(f.index)
    f = f[status.notna() & (status == False)]
    p = price_frame(f.index, date, date, ['close', 'paused'], None).set_index('code').reindex(f.index)
    f = f[(p.close > 0) & (p.paused == 0)]
    start, end = [last_trade_on_or_before(d) for d in momentum_calendar_targets(date)]
    prices = [price_frame(f.index, d, d, ['close'], 'post').set_index('code').close.reindex(f.index) for d in (start, end)]
    f['mom'] = endpoint_return(prices[0], prices[1])
    f = build_groups(f)
    f['formation_date'], f['accounting_year'] = str(date), accounting_year(date)
    f['mom_start_date'], f['mom_end_date'] = str(start), str(end)
    write_file(PREFIX + '_holdings_' + date.strftime('%Y%m%d') + '.csv', f.to_csv(), append=False)
    log.info('NM4形成%s，共同样本%d只，行业%d个，年报%d' % (date, len(f), f.industry.nunique(), accounting_year(date)))
    return {'date': date, 'frame': f}


def industry_adjusted_returns(f, returns):
    r = returns.reindex(f.index)
    industry_ret = {}
    for industry, part in f.groupby('industry'):
        v = r.reindex(part.index)
        industry_ret[industry] = np.nan if (~np.isfinite(v)).any() else float((part.industry_weight * v).sum())
    return r - f.industry.map(industry_ret)


def aggregate_month(f, returns, rf):
    r = returns.reindex(f.index)
    residual = industry_adjusted_returns(f, r)
    row = {'RF': rf}
    row['RM'] = np.nan if (~np.isfinite(r)).any() else float((f.market_weight * r).sum())
    row['MKT'] = row['RM'] - rf
    for factor in FACTORS:
        for group in GROUPS:
            part = f[f[factor + '_group'] == group]
            v = residual.reindex(part.index)
            bad = ~np.isfinite(v)
            w = part[factor + '_weight']
            row[factor + '_' + group] = np.nan if part.empty or bad.any() else float((w * v).sum())
            row[factor + '_' + group + '_missing_weight'] = float(w[bad].sum())
        row[factor] = float(np.sum([row[factor + '_' + k] * sign for k, sign in [('SH', .5), ('BH', .5), ('SL', -.5), ('BL', -.5)]]))
    # jqdata通配导入可能覆盖内置all/sum，显式传入列表并使用NumPy归约。
    row['complete'] = int(np.isfinite([row[k] for k in ('MKT',) + FACTORS]).all())
    return row


def settle_month(end):
    month = end.strftime('%Y-%m')
    if g.snapshot is None or month in g.completed:
        return
    start, f = g.snapshot['date'], g.snapshot['frame']
    if end <= start:
        return
    p = price_frame(f.index, start, end, ['close'], 'post')
    prices = [p[p.date == d].set_index('code').close.reindex(f.index) for d in (start, end)]
    r = endpoint_return(prices[0], prices[1])
    alive = set(get_all_securities(types=['stock'], date=end).index)
    r.loc[[c for c in f.index if c not in alive]] = np.nan
    rf = float(g.rf.get(month, np.nan)) if RF_FILE else (1 + RF_ANNUAL) ** (1 / 12.) - 1
    row = aggregate_month(f, r, rf)
    row.update(month=month, formation_date=str(start), end_date=str(end), n=len(f),
               accounting_year=int(f.accounting_year.iloc[0]),
               mom_start_date=f.mom_start_date.iloc[0], mom_end_date=f.mom_end_date.iloc[0],
               rf_source=RF_FILE or 'constant_assumption', implementation='A_share_monthly_industry_proxy')
    g.rows.append(row)
    write_file(PREFIX + '_monthly.csv', pd.DataFrame(g.rows).to_csv(index=False), append=False)
    g.completed.add(month)
    if row['complete']:
        record(NM_MKT_pct=100*row['MKT'], NM_HML_pct=100*row['HML_NM'],
               NM_MOM_pct=100*row['MOM_NM'], NM_PMU_pct=100*row['PMU'])
    log.info('NM4月收益%s：%s' % (month, {k: row[k] for k in ('MKT',) + FACTORS + ('complete',)}))


def build_targets(f, mode, max_per_leg, invest_ratio):
    selected = {'ALL_LONG': FACTORS, 'VALUE_LONG': ('HML_NM',),
                'MOM_LONG': ('MOM_NM',), 'PROFIT_LONG': ('PMU',)}[mode]
    target = {}
    for factor in selected:
        for group in ('SH', 'BH'):
            part = f[f[factor + '_group'] == group].sort_values('cap', ascending=False)
            if max_per_leg is not None:
                part = part.head(max_per_leg)
            if part.empty:
                raise ValueError('交易分组为空')
            for code, w in (part.cap / part.cap.sum()).items():
                target[code] = target.get(code, 0.) + float(w) * invest_ratio / (2 * len(selected))
    return target


def prepare_month(context):
    date = as_date(context.previous_date)
    if date.month == context.current_dt.month:
        return
    settle_month(date)
    g.snapshot = make_snapshot(date)
    g.target = build_targets(g.snapshot['frame'], TRADE_MODE, MAX_PER_LEG, INVEST_RATIO)
    g.trade_date = context.current_dt.date()
    tax = .0005 if g.trade_date >= dt.date(2023, 8, 28) else .001
    set_order_cost(OrderCost(open_tax=0, close_tax=tax, open_commission=.0003,
                            close_commission=.0003, min_commission=5), type='stock')


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

def momentum_calendar_targets(formation_date):
    """形成月t，持有月t+1：P[t-1月末]/P[t-12月末]-1，跳过形成月。
    例如2026-08-31形成，2026-09持有：2025-08末至2026-07末。
    这是持有月的prior(2-12)，11个月，不是过去1个月或整12个月。
    """
    month = pd.Period(formation_date, freq='M')
    return (month - 12).end_time.date(), (month - 1).end_time.date()

def last_trade_on_or_before(date):
    days = get_trade_days(end_date=date, count=1)
    if len(days) != 1:
        raise ValueError('动量端点交易日历缺失')
    return as_date(days[0])

def endpoint_return(start_price, end_price):
    result = end_price / start_price - 1.0
    good = (start_price > 0) & (end_price > 0) & np.isfinite(start_price) & np.isfinite(end_price)
    return result.where(good)

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

def month_end(context):
    today = context.current_dt.date()
    # 未来交易日历不是未来行情，不查询明日价格或财报。
    following = get_trade_days(start_date=today + dt.timedelta(days=1), count=1)
    if len(following) and as_date(following[0]).month != today.month:
        settle_month(today)
