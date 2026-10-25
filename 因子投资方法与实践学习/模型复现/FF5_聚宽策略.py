from jqdata import *
import datetime as dt
import io
import itertools
import numpy as np
import pandas as pd

MODEL = 'FF5'
PREFIX = 'ff5_book'
ENABLE_TRADING = True
MAX_PER_LEG = 10
INVEST_RATIO = .98
MIN_LIST_DAYS = 365
MIN_UNIVERSE = 120
BATCH = 200
RF_FILE = ''  # 可选研究文件，month,rf；rf为月简单收益小数
RF_ANNUAL = 0.0  # 无文件时的明确假设，默认0不代表取得历史RF
GROUPS6 = ('SL', 'SN', 'SH', 'BL', 'BN', 'BH')
GROUPS18 = tuple(''.join(x) for x in itertools.product('SB', 'LNH', 'LNH'))


def initialize(context):
    if MODEL not in ('FF5', 'HXZ'):
        raise ValueError('请使用生成后的FF5或HXZ独立脚本')
    set_benchmark('000300.XSHG')
    set_option('use_real_price', True)
    set_option('avoid_future_data', True)
    set_slippage(PriceRelatedSlippage(.001))
    log.set_level('order', 'error')
    g.cohort = None
    g.snapshot = None
    g.completed, g.rows, g.target = set(), [], {}
    g.trade_date = None
    g.rf = {}
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
    log.info('%s A股近似版；六月年度标签，组内月度市值权重；RF=%s' % (MODEL, RF_FILE or '常数假设'))


def batches(codes):
    codes = list(codes)
    for i in range(0, len(codes), BATCH):
        yield codes[i:i + BATCH]


def as_date(value):
    return pd.Timestamp(value).date()


def previous_trade(date):
    days = get_trade_days(end_date=date, count=1)
    if not len(days):
        raise ValueError('交易日历缺失')
    return as_date(days[-1])


def june_year(date):
    # 输入是月末形成日；六月最后交易日可能早于6月30日。
    return date.year if date.month >= 6 else date.year - 1


def caps_on(codes, date):
    rows = []
    for part in batches(codes):
        q = query(valuation.code, valuation.market_cap).filter(valuation.code.in_(part))
        frame = get_fundamentals(q, date=str(date))
        if frame is None:
            raise ValueError('市值接口返回None')
        rows.append(frame)
    if not rows:
        raise ValueError('空市值请求')
    f = pd.concat(rows, ignore_index=True).set_index('code')
    if f.index.duplicated().any():
        raise ValueError('市值记录重复')
    return f.market_cap * 1e8  # 财报与市值统一为元


def market_universe(date):
    u = get_all_securities(types=['stock'], date=date)
    codes = [c for c in u.index if
             ((c.endswith('.XSHG') and c.startswith(('600', '601', '603', '605'))) or
              (c.endswith('.XSHE') and c.startswith(('000', '001', '002', '003', '300', '301'))))
             and (date - as_date(u.loc[c, 'start_date'])).days >= MIN_LIST_DAYS]
    if not codes:
        raise ValueError('历史股票池为空')
    st = get_extras('is_st', codes, start_date=str(date), end_date=str(date), df=True)
    if st is None or st.empty:
        raise ValueError('历史ST状态缺失')
    status = st.iloc[-1].reindex(codes)
    codes = status.index[status.notna() & (status == False)].tolist()
    cap = caps_on(codes, date).reindex(codes)
    cap = cap[np.isfinite(cap) & (cap > 0)]
    if len(cap) < MIN_UNIVERSE:
        raise ValueError('历史市场样本不足')
    return cap


def validated_history(history, asof, required):
    missing = set(['code', 'statDate'] + required) - set(history.columns)
    if missing:
        raise ValueError('财报字段缺失：' + str(sorted(missing)))
    h = history.copy()
    h['statDate'] = pd.to_datetime(h.statDate, errors='raise')
    if h.statDate.isna().any() or (h.statDate > pd.Timestamp(asof)).any():
        raise ValueError('财报报告期为空或在未来')
    if h.duplicated(['code', 'statDate']).any():
        raise ValueError('重复报告期，必须先核查版本')
    # watch_date是主要披露时点约束；返回pubDate时再显式验证。
    if 'pubDate' in h.columns:
        p = pd.to_datetime(h.pubDate, errors='coerce')
        if p.isna().any() or (p > pd.Timestamp(asof)).any():
            raise ValueError('财报公告日为空或晚于观察日')
    return h


def annual_features(history, year, asof, model):
    required = ['total_assets']
    if model == 'FF5':
        required += ['equities_parent_company_owners', 'operating_revenue',
                     'operating_cost', 'sale_expense', 'administration_expense', 'financial_expense']
    h = validated_history(history, asof, required)
    current = h[h.statDate == pd.Timestamp(year, 12, 31)].set_index('code')
    prior = h[h.statDate == pd.Timestamp(year - 1, 12, 31)].set_index('code')
    f = pd.DataFrame(index=current.index)
    f['assets'] = current.total_assets
    f['assets_prev'] = prior.total_assets.reindex(f.index)
    f['inv'] = f.assets / f.assets_prev - 1
    f.loc[(f.assets <= 0) | (f.assets_prev <= 0), 'inv'] = np.nan
    if model == 'FF5':
        f['equity'] = current.equities_parent_company_owners
        # finance expense为利息费用代理，非原论文精确会计定义。
        expense_cols = ['operating_cost', 'sale_expense', 'administration_expense', 'financial_expense']
        f['op_numerator'] = current.operating_revenue - current[expense_cols].sum(axis=1, skipna=False)
        f['op'] = f.op_numerator / f.equity
        f.loc[f.equity <= 0, 'op'] = np.nan
    f['accounting_year'] = year
    return f.replace([np.inf, -np.inf], np.nan)


def fetch_annual(codes, date, model):
    fields = [balance.total_assets]
    if model == 'FF5':
        fields += [balance.equities_parent_company_owners, income.operating_revenue,
                   income.operating_cost, income.sale_expense,
                   income.administration_expense, income.financial_expense]
    rows = []
    for part in batches(codes):
        data = get_history_fundamentals(part, fields=fields, watch_date=str(date),
                                        count=3, interval='1y', stat_by_year=True)
        if data is None:
            raise ValueError('年报接口返回None')
        rows.append(data)
    h = pd.concat(rows, ignore_index=True)
    # 留下原始接口结果供审计，禁止四季度单季流量冒充全年。
    write_file(PREFIX + '_annual_raw_' + str(date) + '.csv', h.to_csv(index=False), append=False)
    return annual_features(h, date.year - 1, date, model)


def quarterly_roe(history, date):
    h = validated_history(history, date, ['np_parent_company_owners', 'equities_parent_company_owners'])
    rows = []
    earliest = pd.Timestamp(date) - pd.DateOffset(months=6)
    for code, part in h.groupby('code'):
        part = part.sort_values('statDate').tail(2)
        if len(part) != 2:
            continue
        last, prev = part.iloc[-1], part.iloc[0]
        if last.statDate.to_period('Q').ordinal - prev.statDate.to_period('Q').ordinal != 1:
            continue
        if last.statDate < earliest:
            continue
        earnings, equity = last.np_parent_company_owners, prev.equities_parent_company_owners
        if not np.isfinite(earnings) or not np.isfinite(equity) or equity <= 0:
            continue
        rows.append([code, earnings / equity, earnings, equity, str(last.statDate.date())])
    return pd.DataFrame(rows, columns=['code', 'roe', 'quarter_earnings', 'lag_equity', 'roe_report_date']).set_index('code')


def fetch_quarterly(codes, date):
    rows = []
    for part in batches(codes):
        h = get_history_fundamentals(part, fields=[income.np_parent_company_owners,
                                    balance.equities_parent_company_owners], watch_date=str(date),
                                    count=2, interval='1q', stat_by_year=False)
        if h is None:
            raise ValueError('季报接口返回None')
        rows.append(h)
    h = pd.concat(rows, ignore_index=True)
    write_file(PREFIX + '_quarter_raw_' + str(date) + '.csv', h.to_csv(index=False), append=False)
    return quarterly_roe(h, date)


def three_bins(signal):
    valid = signal[np.isfinite(signal)]
    if len(valid) < 6:
        raise ValueError('分组有效信号不足')
    low, high = valid.quantile([.3, .7])
    bins = pd.Series(np.where(valid <= low, 'L', np.where(valid > high, 'H', 'N')), index=valid.index)
    if set(bins) != set('LNH'):
        raise ValueError('信号断点重复导致分组为空')
    return bins.reindex(signal.index), low, high


def annual_labels(frame, model):
    f = frame.copy()
    cut = f.cap.median()
    f['size'] = np.where(f.cap <= cut, 'S', 'B')
    f['size_cut'] = cut
    fields = ['bm', 'op', 'inv'] if model == 'FF5' else ['inv']
    for field in fields:
        bins, lo, hi = three_bins(f[field])
        f[field + '_bin'] = bins
        f[field + '_group'] = f['size'] + bins
        f[field + '_cut30'], f[field + '_cut70'] = lo, hi
        if set(f[field + '_group'].dropna()) != set(GROUPS6):
            raise ValueError(field + '年度六组不完整')
    return f


def ensure_cohort(date):
    year = june_year(date)
    if g.cohort is not None and g.cohort['year'] == year:
        return g.cohort
    formation = previous_trade(dt.date(year, 6, 30))
    if formation > date:
        raise ValueError('年度形成日在未来')
    cap = market_universe(formation)
    f = pd.DataFrame({'cap': cap}).join(fetch_annual(cap.index, formation, MODEL))
    if MODEL == 'FF5':
        december = previous_trade(dt.date(year - 1, 12, 31))
        f['dec_cap'] = caps_on(f.index, december).reindex(f.index)
        f['bm'] = f.equity / f.dec_cap
        f.loc[(f.equity <= 0) | (f.dec_cap <= 0), 'bm'] = np.nan
    f = annual_labels(f.replace([np.inf, -np.inf], np.nan), MODEL)
    f['annual_formation'] = str(formation)
    f = f.rename(columns={'cap': 'june_cap'})
    write_file(PREFIX + '_annual_groups_' + str(year) + '.csv', f.to_csv(), append=False)
    g.cohort = {'year': year, 'date': formation, 'frame': f}
    return g.cohort


def grouped_weights(f, column, expected):
    weights = pd.DataFrame(0., index=f.index, columns=expected)
    for group in expected:
        members = f.index[f[column] == group]
        if not len(members):
            raise ValueError('组合为空：' + column + '/' + group)
        cap = f.loc[members, 'cap']
        if (~np.isfinite(cap)).any() or (cap <= 0).any():
            raise ValueError('组合市值无效')
        weights.loc[members, group] = cap / cap.sum()
    return weights


def construct_portfolios(frame, market_cap, model):
    f = frame.copy()
    columns = {}
    if model == 'FF5':
        for field in ('bm', 'op', 'inv'):
            w = grouped_weights(f, field + '_group', GROUPS6)
            for group in GROUPS6:
                columns[field + '_' + group] = w[group]
    else:
        f = f[np.isfinite(f.roe) & f.inv_bin.notna()].copy()
        bins, lo, hi = three_bins(f.roe)
        f['roe_bin'] = bins
        f['roe_cut30'], f['roe_cut70'] = lo, hi
        f['q_group'] = f['size'] + f.inv_bin + bins
        w = grouped_weights(f, 'q_group', GROUPS18)
        for group in GROUPS18:
            columns['q_' + group] = w[group]
    columns['MARKET'] = market_cap / market_cap.sum()
    weights = pd.DataFrame(columns).fillna(0.)
    return f, weights


def factor_coefficients(model):
    """组合收益线性映射到因子；不把FF3 SMB直接沿用到FF5。"""
    if model == 'FF5':
        c = pd.DataFrame(0., index=[f + '_' + g for f in ('bm', 'op', 'inv') for g in GROUPS6],
                         columns=['SMB', 'HML', 'RMW', 'CMA'])
        for field in ('bm', 'op', 'inv'):
            for group in GROUPS6:
                c.loc[field + '_' + group, 'SMB'] = (1 if group[0] == 'S' else -1) / 9.
        for field, factor, direction in [('bm', 'HML', 1), ('op', 'RMW', 1), ('inv', 'CMA', -1)]:
            for size in 'SB':
                c.loc[field + '_' + size + 'H', factor] = direction / 2.
                c.loc[field + '_' + size + 'L', factor] = -direction / 2.
    else:
        c = pd.DataFrame(0., index=['q_' + g for g in GROUPS18], columns=['ME', 'IA', 'ROE'])
        for group in GROUPS18:
            c.loc['q_' + group, 'ME'] = (1 if group[0] == 'S' else -1) / 9.
            c.loc['q_' + group, 'IA'] = {'L': 1/6., 'N': 0., 'H': -1/6.}[group[1]]
            c.loc['q_' + group, 'ROE'] = {'L': -1/6., 'N': 0., 'H': 1/6.}[group[2]]
    return c


def aggregate_month(weights, returns, rf, model):
    r = returns.reindex(weights.index)
    row, portfolio_returns = {'RF': rf}, {}
    for column in weights:
        w = weights[column]
        active = w > 0
        bad = active & ~np.isfinite(r)
        value = np.nan if bad.any() else float((w[active] * r[active]).sum())
        portfolio_returns[column] = value
        row['P_' + column] = value
        row['missing_' + column] = float(w[bad].sum())
    row['RM'] = portfolio_returns['MARKET']
    row['MKT'] = row['RM'] - rf
    c = factor_coefficients(model)
    for factor in c:
        use = c.index[c[factor] != 0]
        values = np.array([portfolio_returns[k] for k in use])
        row[factor] = float(np.dot(values, c.loc[use, factor])) if np.isfinite(values).all() else np.nan
    # jqdata通配导入可能覆盖内置all；显式对有限值数组归约。
    row['complete'] = int(np.isfinite([row[k] for k in ['MKT'] + list(c.columns)]).all())
    return row


def build_targets(weights, model):
    if model == 'FF5':
        legs = ['bm_SH', 'bm_BH', 'op_SH', 'op_BH', 'inv_SL', 'inv_BL']
    else:
        # 六个低投资组、六个高盈利组各占一半；交叉成员累加。
        legs = ['q_' + g for g in GROUPS18 if g[1] == 'L'] + ['q_' + g for g in GROUPS18 if g[2] == 'H']
    target = pd.Series(0., index=weights.index)
    for leg in legs:
        w = weights.loc[weights[leg] > 0, leg].sort_values(ascending=False)
        if MAX_PER_LEG is not None:
            w = w.head(MAX_PER_LEG)
        if w.empty:
            raise ValueError('交易腿为空')
        target.loc[w.index] += w / w.sum() * INVEST_RATIO / len(legs)
    return target[target > 0].to_dict()


def make_snapshot(date):
    annual = ensure_cohort(date)
    # 市场独立取样；不要求市场股票具有全部财报，不用风格子样本代替市场。
    market = market_universe(date)
    f = annual['frame'].copy()
    alive = set(get_all_securities(types=['stock'], date=date).index)
    f = f.loc[[c for c in f.index if c in alive]].copy()
    # 只在形成前移除已退市者；持有期内退市保留缺失收益。
    f['cap'] = caps_on(f.index, date).reindex(f.index)
    if (~np.isfinite(f.cap)).any() or (f.cap <= 0).any():
        raise ValueError('年度股票池月末市值缺失，禁止静默删除后重配权重')
    if MODEL == 'HXZ':
        f = f.join(fetch_quarterly(f.index, date))
    f, weights = construct_portfolios(f, market, MODEL)
    factor_weights = weights.drop(columns=['MARKET']).dot(factor_coefficients(MODEL))
    factor_weights['MKT_stock_weight'] = weights.MARKET
    tag = date.strftime('%Y%m%d')
    write_file(PREFIX + '_features_' + tag + '.csv', f.to_csv(), append=False)
    write_file(PREFIX + '_portfolios_' + tag + '.csv', weights.to_csv(), append=False)
    write_file(PREFIX + '_factor_weights_' + tag + '.csv', factor_weights.to_csv(), append=False)
    log.info('%s %s：年度形成%s，风格股票%d，市场股票%d' % (MODEL, date, annual['date'], len(f), len(market)))
    return {'date': date, 'annual_date': annual['date'], 'weights': weights}


def closes(codes, date):
    frames = []
    for part in batches(codes):
        p = get_price(part, start_date=str(date), end_date=str(date), frequency='daily',
                      fields=['close'], skip_paused=False, fq='post', panel=False)
        if p is None or not {'code', 'time', 'close'}.issubset(p.columns):
            raise ValueError('需要panel=False的time/code/close行情长表')
        frames.append(p)
    p = pd.concat(frames, ignore_index=True)
    if p.duplicated(['code', 'time']).any():
        raise ValueError('行情重复')
    p = p[pd.to_datetime(p.time).dt.date == date]
    return p.set_index('code').close.reindex(codes)


def settle_month(end):
    month = end.strftime('%Y-%m')
    if g.snapshot is None or month in g.completed or end <= g.snapshot['date']:
        return
    s, w = g.snapshot['date'], g.snapshot['weights']
    a, b = closes(w.index, s), closes(w.index, end)
    r = (b / a - 1).where((a > 0) & (b > 0) & np.isfinite(a) & np.isfinite(b))
    alive = set(get_all_securities(types=['stock'], date=end).index)
    r.loc[[code for code in w.index if code not in alive]] = np.nan
    rf = float(g.rf.get(month, np.nan)) if RF_FILE else (1 + RF_ANNUAL) ** (1/12.) - 1
    row = aggregate_month(w, r, rf, MODEL)
    row.update(month=month, model=MODEL, formation_date=str(s), end_date=str(end),
               annual_formation=str(g.snapshot['annual_date']), n_union=len(w),
               rf_source=RF_FILE or 'constant_assumption', accounting='A_share_proxy',
               weighting='monthly_market_cap', price_return='jq_post_adjusted_proxy')
    g.rows.append(row)
    write_file(PREFIX + '_monthly.csv', pd.DataFrame(g.rows).to_csv(index=False), append=False)
    g.completed.add(month)
    factors = ['MKT'] + list(factor_coefficients(MODEL).columns)
    if row['complete']:
        record(**dict((MODEL + '_' + k + '_pct', 100 * row[k]) for k in factors))
    log.info('%s %s complete=%s %s' % (MODEL, month, row['complete'], {k: row[k] for k in factors}))


def prepare_month(context):
    g.trade_date, g.target = None, {}
    date = as_date(context.previous_date)
    if date.month == context.current_dt.month:
        return
    settle_month(date)
    g.snapshot = make_snapshot(date)
    g.target = build_targets(g.snapshot['weights'], MODEL) if ENABLE_TRADING else {}
    g.trade_date = context.current_dt.date()
    tax = .0005 if g.trade_date >= dt.date(2023, 8, 28) else .001
    set_order_cost(OrderCost(open_tax=0, close_tax=tax, open_commission=.0003,
                            close_commission=.0003, min_commission=5), type='stock')


def sell_orders(context):
    if not ENABLE_TRADING or g.trade_date != context.current_dt.date():
        return
    data, nav = get_current_data(), context.portfolio.total_value
    for code, pos in list(context.portfolio.positions.items()):
        q, value = data[code], g.target.get(code, 0.) * nav
        if pos.value > value and not q.paused and q.last_price > q.low_limit:
            order_target_value(code, value)


def buy_orders(context):
    if not ENABLE_TRADING or g.trade_date != context.current_dt.date():
        return
    data, nav = get_current_data(), context.portfolio.total_value
    for code, weight in sorted(g.target.items(), key=lambda item: -item[1]):
        q = data[code]
        if q.paused or q.is_st or '退' in q.name or not (q.low_limit < q.last_price < q.high_limit):
            continue
        pos = context.portfolio.positions.get(code)
        held = pos.value if pos else 0.
        amount = min(weight * nav - held, context.portfolio.available_cash * .995)
        if amount >= q.last_price * 100 + 5:
            order_target_value(code, held + amount)
    # 单次调仓，不在日内或后续日期追单；不足100股、费用等会留下现金。


def month_end(context):
    today = context.current_dt.date()
    days = get_trade_days(start_date=today + dt.timedelta(days=1), count=1)
    if len(days) and as_date(days[0]).month != today.month:
        settle_month(today)
