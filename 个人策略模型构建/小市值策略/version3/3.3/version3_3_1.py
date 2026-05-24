from jqdata import *
import torch
import torch.nn as nn
from torch.nn.utils import weight_norm
import numpy as np
import io

# ---------------------------------------------------------
# 1. TCN + Attention 模型架构定义 (保持一致)
# ---------------------------------------------------------
class ChainedCausalConv(nn.Module):
    def __init__(self, n_inputs, n_outputs, kernel_size, stride, dilation, padding, dropout=0.2):
        super(ChainedCausalConv, self).__init__()
        self.conv1 = weight_norm(nn.Conv1d(n_inputs, n_outputs, kernel_size, stride=stride, padding=padding, dilation=dilation))
        self.chomp1 = nn.ConstantPad1d((-padding, 0), 0)
        self.relu1 = nn.ReLU()
        self.dropout1 = nn.Dropout(dropout)
        self.conv2 = weight_norm(nn.Conv1d(n_outputs, n_outputs, kernel_size, stride=stride, padding=padding, dilation=dilation))
        self.chomp2 = nn.ConstantPad1d((-padding, 0), 0)
        self.relu2 = nn.ReLU()
        self.dropout2 = nn.Dropout(dropout)
        self.net = nn.Sequential(self.conv1, self.chomp1, self.relu1, self.dropout1, self.conv2, self.chomp2, self.relu2, self.dropout2)
        self.downsample = nn.Conv1d(n_inputs, n_outputs, 1) if n_inputs != n_outputs else None
        self.relu = nn.ReLU()

    def forward(self, x):
        return self.relu(self.net(x) + (x if self.downsample is None else self.downsample(x)))

class TemporalAttention(nn.Module):
    def __init__(self, hidden_size):
        super(TemporalAttention, self).__init__()
        self.attention = nn.Sequential(
            nn.Linear(hidden_size, hidden_size // 2),
            nn.Tanh(),
            nn.Linear(hidden_size // 2, 1)
        )

    def forward(self, x):
        x_transposed = x.transpose(1, 2)
        attn_weights = self.attention(x_transposed)
        attn_weights = torch.softmax(attn_weights, dim=1)
        context = torch.sum(x_transposed * attn_weights, dim=1)
        return context, attn_weights

class TCNModel(nn.Module):
    def __init__(self, input_size, output_size, num_channels, kernel_size=3, dropout=0.2):
        super(TCNModel, self).__init__()
        layers = []
        for i in range(len(num_channels)):
            dilation_size = 2 ** i
            in_channels = input_size if i == 0 else num_channels[i-1]
            layers += [ChainedCausalConv(in_channels, num_channels[i], kernel_size, stride=1, dilation=dilation_size, padding=(kernel_size-1) * dilation_size, dropout=dropout)]
        self.tcn = nn.Sequential(*layers)
        self.attention = TemporalAttention(num_channels[-1])
        self.linear = nn.Linear(num_channels[-1], output_size)

    def forward(self, x):
        tcn_out = self.tcn(x)
        context, attn_weights = self.attention(tcn_out)
        return self.linear(context)

# ---------------------------------------------------------
# 2. 策略初始化与全局变量
# ---------------------------------------------------------
def initialize(context):
    set_benchmark('000905.XSHG')
    set_option('use_real_price', True)
    set_order_cost(OrderCost(close_tax=0.001, open_commission=0.0003, close_commission=0.0003, min_commission=5), type='stock')
    
    g.stock_num = 10            
    g.seq_length = 30           
    g.feature_num = 6           
    
    # 跟踪每只持仓股买入后的历史最高价，用于动态止损
    g.last_high_prices = {}
    g.stop_loss_pct = 0.25     # 动态止损阈值：从最高点回撤 25% 
    
    g.model = TCNModel(input_size=g.feature_num, output_size=1, num_channels=[16, 32, 64])
    
    try:
        weight_file = 'tcn_attention_weights.pth'
        file_bytes = read_file(weight_file)
        g.model.load_state_dict(torch.load(io.BytesIO(file_bytes)))
        g.model.eval() 
        print(f"🎉 注意力版大模型接入成功，已启用非均匀执行层优化。")
    except Exception as e:
        print(f"❌ 权重加载失败: {e}")
        raise e
        
    # 核心定时任务
    run_monthly(rebalance, monthday=1, time='09:30') # 每月月初大调仓
    run_daily(daily_market_check, time='14:50')     # 每天尾盘清算巡逻（动态止损）

# ---------------------------------------------------------
# 3. 核心大调仓层（置信度非均匀配资）
# ---------------------------------------------------------
def rebalance(context):
    # A. 宏观风控大盾
    index_data = attribute_history('000300.XSHG', 60, '1d', ['close'])
    if index_data['close'][-1] < index_data['close'].mean():
        print(f"🚨 {context.current_dt.date()}: 大盘走弱，清仓所有持仓。")
        for stock in list(context.portfolio.positions.keys()):
            order_target_value(stock, 0)
        g.last_high_prices.clear()
        return

    # B. 获取预滤波候选池
    curr_data = get_current_data()
    q = query(valuation.code).filter(
        indicator.roe > 5.0, indicator.roa > 3.0
    ).order_by(valuation.market_cap.asc()).limit(150)
    
    raw_pool = [s.code for s in get_fundamentals(q).itertuples() if not curr_data[s.code].is_st and not curr_data[s.code].paused]
    if not raw_pool: return

    # C. 批量提取多维时序特征
    df_price = get_price(raw_pool, end_date=context.previous_date, frequency='daily', 
                         fields=['open', 'close', 'high', 'low', 'volume', 'money'], count=g.seq_length, panel=False)
    
    X_list, valid_stocks = [], []
    for stock, group in df_price.groupby('code'):
        if len(group) < g.seq_length: continue
        data = group[['open', 'close', 'high', 'low', 'volume', 'money']].values
        X_list.append((data - np.mean(data, axis=0)) / (np.std(data, axis=0) + 1e-8))
        valid_stocks.append(stock)

    if not X_list: return
    batch_X = torch.tensor(np.array(X_list), dtype=torch.float32).transpose(1, 2)

    # D. TCN+Attention 推理打分
    scores = {}
    with torch.no_grad():
        preds = g.model(batch_X).squeeze().numpy()
        if preds.ndim == 0: preds = [preds.item()]
        for i, stock in enumerate(valid_stocks): 
            scores[stock] = preds[i]

    # E. 最终名额排序 (Top 10)
    final_buy_list = sorted(scores, key=scores.get, reverse=True)[:g.stock_num]
    
    # ---------------------------------------------------------
    # 【非均匀分配核心】：对前 10 名的 Logit 分数进行 截面 Softmax
    # ---------------------------------------------------------
    top_scores = np.array([scores[stock] for stock in final_buy_list])
    # 减去最大值防止指数爆炸
    exp_scores = np.exp(top_scores - np.max(top_scores))
    softmax_weights = exp_scores / np.sum(exp_scores)
    
    # 映射得到每只股票对应的资金配比字典
    allocation_dict = dict(zip(final_buy_list, softmax_weights))

    # F. 执行换仓交易
    # 1. 先清仓不在最新 Top10 名单中的股票
    for stock in list(context.portfolio.positions.keys()):
        if stock not in final_buy_list:
            order_target_value(stock, 0)
            if stock in g.last_high_prices:
                del g.last_high_prices[stock]
            
    # 2. 根据置信度权重调整或买入目标股票
    total_value = context.portfolio.total_value
    for stock in final_buy_list:
        target_money = total_value * allocation_dict[stock]
        order_target_value(stock, target_money)
        
        # 如果是新买入的股票，初始化其最高价跟踪器
        if stock not in g.last_high_prices and stock in context.portfolio.positions:
            g.last_high_prices[stock] = context.portfolio.positions[stock].price
            
    print(f"💡 大调仓完毕。本期最笃定标的: {final_buy_list[0]} (配资比例: {allocation_dict[final_buy_list[0]]*100:.2f}%)")

# ---------------------------------------------------------
# 4. 日度换仓巡逻层（移动止损安全网）
# ---------------------------------------------------------
def daily_market_check(context):
    if not context.portfolio.positions: return
    
    curr_data = get_current_data()
    stocks_to_sell = []
    
    for stock in list(context.portfolio.positions.keys()):
        current_price = curr_data[stock].last_price
        
        # 边缘保护：若获取不到当天现价或停牌则跳过
        if np.isnan(current_price) or current_price == 0: continue
        
        # 初始化或更新该股票自持仓以来的历史最高价
        if stock not in g.last_high_prices:
            g.last_high_prices[stock] = current_price
        else:
            g.last_high_prices[stock] = max(g.last_high_prices[stock], current_price)
            
        # 计算当前价格相较于最高点的回撤幅度
        high_price = g.last_high_prices[stock]
        drawdown = (high_price - current_price) / high_price
        
        # 如果回撤超标，打入斩仓名单
        if drawdown >= g.stop_loss_pct:
            stocks_to_sell.append(stock)
            
    # 执行斩仓动作
    if stocks_to_sell:
        print(f"✂️ 巡逻兵触发日内动态移动止损，斩仓标的: {stocks_to_sell}")
        for stock in stocks_to_sell:
            order_target_value(stock, 0)
            if stock in g.last_high_prices:
                del g.last_high_prices[stock]
