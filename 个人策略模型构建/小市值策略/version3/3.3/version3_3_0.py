# ======================================================================
# 【策略回测专享】TCN + Temporal Attention 智能策略 (沙箱穿透版)
# ======================================================================
from jqdata import *
import torch
import torch.nn as nn
from torch.nn.utils import weight_norm
import numpy as np
import io

# ---------------------------------------------------------
# 1. 神经网络架构定义 (必须与训练端代码严格百分百保持一致)
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
# 2. 策略初始化与沙箱桥接
# ---------------------------------------------------------
def initialize(context):
    set_benchmark('000905.XSHG')
    set_option('use_real_price', True)
    set_order_cost(OrderCost(close_tax=0.001, open_commission=0.0003, close_commission=0.0003, min_commission=5), type='stock')
    
    # 策略核心参数设定
    g.stock_num = 10            # 目标持仓股票数
    g.seq_length = 30           # 历史特征步长
    g.feature_num = 6           # 特征通道数: OHLCV + Money
    
    # 初始化未经受训的模型外壳
    g.model = TCNModel(input_size=g.feature_num, output_size=1, num_channels=[16, 32, 64])
    
    # 【穿透核心】：将研究环境生成的注意力版模型灵魂导入回测沙箱
    try:
        weight_file = 'tcn_attention_weights.pth'
        file_bytes = read_file(weight_file)
        g.model.load_state_dict(torch.load(io.BytesIO(file_bytes)))
        g.model.eval() # 锁定为推理模式，阻断反向传播与 Dropout 随机性
        print(f"🎉 成功穿透沙箱，注意力版 TCN 模型初始化圆满！")
    except Exception as e:
        print(f"❌ 灵魂接入发生崩塌，请确认研究环境中已跑完训练。报错信息: {e}")
        raise e
        
    # 定期调仓：每月第一个交易日运行
    run_monthly(rebalance, monthday=1, time='09:30')

# ---------------------------------------------------------
# 3. 核心向量化调仓层
# ---------------------------------------------------------
def rebalance(context):
    # --- A. 宏观风控大盾 (大盘处于均线之下坚决彻底空仓) ---
    index_data = attribute_history('000300.XSHG', 60, '1d', ['close'])
    if index_data['close'][-1] < index_data['close'].mean():
        print(f"{context.current_dt.date()}: 大盘安全线破位，执行绝对空仓防守。")
        for stock in context.portfolio.positions:
            order_target_value(stock, 0)
        return

    # --- B. 获取小市值高质量股票候选池 ---
    curr_data = get_current_data()
    q = query(valuation.code).filter(
        indicator.roe > 5.0, 
        indicator.roa > 3.0
    ).order_by(valuation.market_cap.asc()).limit(150)
    
    raw_pool = [s.code for s in get_fundamentals(q).itertuples() 
                if not curr_data[s.code].is_st and not curr_data[s.code].paused]
    
    if not raw_pool: return

    # --- C. 向量化批量获取多维时序特征 ---
    df_price = get_price(raw_pool, end_date=context.previous_date, frequency='daily', 
                         fields=['open', 'close', 'high', 'low', 'volume', 'money'], 
                         count=g.seq_length, panel=False)
    
    X_list, valid_stocks = [], []
    for stock, group in df_price.groupby('code'):
        if len(group) < g.seq_length: continue
        
        # 局部 Z-Score 标准化 (严格保持历史时空平移不变性)
        data = group[['open', 'close', 'high', 'low', 'volume', 'money']].values
        norm_data = (data - np.mean(data, axis=0)) / (np.std(data, axis=0) + 1e-8)
        
        X_list.append(norm_data)
        valid_stocks.append(stock)

    if not X_list: return
    
    # 构造高性能 3D 张量并改变形状适配 Conv1d: (N, T, F) -> (N, F, T)
    batch_X = torch.tensor(np.array(X_list), dtype=torch.float32).transpose(1, 2)

    # --- D. 注意力矩阵高性能批量推理 ---
    scores = {}
    with torch.no_grad():
        preds = g.model(batch_X).squeeze().numpy()
        if preds.ndim == 0: preds = [preds.item()]
        
        for i, stock in enumerate(valid_stocks):
            scores[stock] = preds[i]

    # --- E. 精准狙击与调仓执行 ---
    # 挑选出注意力神经网络给出的评分最高（相对胜率最大）的 10 只股票
    final_buy_list = sorted(scores, key=scores.get, reverse=True)[:g.stock_num]
    
    # 淘汰非标股票
    for stock in context.portfolio.positions:
        if stock not in final_buy_list:
            order_target_value(stock, 0)
            
    # 等权重配资买入
    if final_buy_list:
        target_value = context.portfolio.total_value / len(final_buy_list)
        for stock in final_buy_list:
            order_target_value(stock, target_value)
            
    print(f"💡 调仓完毕。本期 TCN+Attention 评选的核心龙头标的为: {final_buy_list[:3]}")