from jqdata import *
import torch
import torch.nn as nn
from torch.nn.utils import weight_norm
import numpy as np
import io

# ---------------------------------------------------------
# 1. TCN 模型架构定义 (必须与离线训练端代码严格保持一致)
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

class TCNModel(nn.Module):
    def __init__(self, input_size, output_size, num_channels, kernel_size=3, dropout=0.2):
        super(TCNModel, self).__init__()
        layers = []
        for i in range(len(num_channels)):
            dilation_size = 2 ** i
            in_channels = input_size if i == 0 else num_channels[i-1]
            layers += [ChainedCausalConv(in_channels, num_channels[i], kernel_size, stride=1, dilation=dilation_size, padding=(kernel_size-1) * dilation_size, dropout=dropout)]
        self.tcn = nn.Sequential(*layers)
        self.linear = nn.Linear(num_channels[-1], output_size)

    def forward(self, x): return self.linear(self.tcn(x)[:, :, -1])

# ---------------------------------------------------------
# 2. 策略初始化
# ---------------------------------------------------------
def initialize(context):
    # 设定基准与交易成本
    set_benchmark('000905.XSHG')
    set_option('use_real_price', True)
    set_order_cost(OrderCost(close_tax=0.001, open_commission=0.0003, close_commission=0.0003, min_commission=5), type='stock')
    
    # 策略核心参数
    g.stock_num = 10            # 持股数量
    g.seq_length = 30           # 历史观察窗口 (30天)
    g.feature_num = 6           # 特征数量: OHLCV + Money
    
    # 实例化模型
    g.model = TCNModel(input_size=g.feature_num, output_size=1, num_channels=[16, 32, 64])
    
    # 穿透隔离沙箱读取研究环境下的权重文件
    try:
        weight_file = 'tcn_classification_aligned_weights.pth'
        file_bytes = read_file(weight_file)
        g.model.load_state_dict(torch.load(io.BytesIO(file_bytes)))
        g.model.eval() # 锁定为推理模式
        print(f"✅ 孤尘老师，深度学习大脑加载成功。权重来源: {weight_file}")
    except Exception as e:
        print(f"❌ 权重加载失败，请检查研究环境根目录是否存在对应文件。错误信息: {e}")
        raise e
        
    # 每月第一个交易日执行调仓
    run_monthly(rebalance, monthday=1, time='09:30')

# ---------------------------------------------------------
# 3. 核心执行逻辑
# ---------------------------------------------------------
def rebalance(context):
    # --- A. 宏观风控 (基于沪深300指数的60日均线) ---
    index_data = attribute_history('000300.XSHG', 60, '1d', ['close'])
    if index_data['close'][-1] < index_data['close'].mean():
        print(f"{context.current_dt.date()}: 宏观趋势走弱，执行空仓防守。")
        for stock in context.portfolio.positions:
            order_target_value(stock, 0)
        return

    # --- B. 构造高概率候选池 (ROE > 5%, ROA > 3%, 最小市值150只) ---
    curr_data = get_current_data()
    q = query(valuation.code).filter(
        indicator.roe > 5.0, 
        indicator.roa > 3.0
    ).order_by(valuation.market_cap.asc()).limit(150)
    
    raw_pool = [s.code for s in get_fundamentals(q).itertuples() 
                if not curr_data[s.code].is_st and not curr_data[s.code].paused]
    
    if not raw_pool: return

    # --- C. 向量化批量获取特征张量 ---
    # 获取过去30天的行情数据
    df_price = get_price(raw_pool, end_date=context.previous_date, frequency='daily', 
                         fields=['open', 'close', 'high', 'low', 'volume', 'money'], 
                         count=g.seq_length, panel=False)
    
    X_list, valid_stocks = [], []
    for stock, group in df_price.groupby('code'):
        if len(group) < g.seq_length: continue
        
        # 提取特征并执行局部标准化 (严格对齐训练时的逻辑)
        data = group[['open', 'close', 'high', 'low', 'volume', 'money']].values
        norm_data = (data - np.mean(data, axis=0)) / (np.std(data, axis=0) + 1e-8)
        
        X_list.append(norm_data)
        valid_stocks.append(stock)

    if not X_list: return
    
    # 构建 Batch Tensor 并进行维度转置 (N, T, F) -> (N, F, T)
    batch_X = torch.tensor(np.array(X_list), dtype=torch.float32).transpose(1, 2)

    # --- D. TCN 智能评分 ---
    scores = {}
    with torch.no_grad():
        preds = g.model(batch_X).squeeze().numpy()
        # 处理单样本边缘情况
        if preds.ndim == 0: preds = [preds.item()]
        
        for i, stock in enumerate(valid_stocks):
            scores[stock] = preds[i]

    # --- E. 择优录取与交易执行 ---
    # 选取模型认为进入截面排名前30%概率最高的 Top 10
    final_buy_list = sorted(scores, key=scores.get, reverse=True)[:g.stock_num]
    
    # 卖出不在名单中的持仓
    for stock in context.portfolio.positions:
        if stock not in final_buy_list:
            order_target_value(stock, 0)
            
    # 等权重买入目标股
    if final_buy_list:
        target_value = context.portfolio.total_value / len(final_buy_list)
        for stock in final_buy_list:
            order_target_value(stock, target_value)
            
    print(f"💡 本次选股完成，TCN 评分前三名: {final_buy_list[:3]}")
