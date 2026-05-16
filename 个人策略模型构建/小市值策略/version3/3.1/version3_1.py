
# 导入基础库
from jqdata import *
import torch
import torch.nn as nn
import numpy as np
import pandas as pd
import io
from torch.nn.utils import weight_norm

# ======================== 1. TCN 模型架构定义 ========================
class ChainedCausalConv(nn.Module):
    """因果残差块：确保模型不偷看未来数据"""
    def __init__(self, n_inputs, n_outputs, kernel_size, stride, dilation, padding, dropout=0.2):
        super(ChainedCausalConv, self).__init__()
        # 第一层膨胀因果卷积
        self.conv1 = weight_norm(nn.Conv1d(n_inputs, n_outputs, kernel_size,
                                           stride=stride, padding=padding, dilation=dilation))
        self.chomp1 = nn.ConstantPad1d((-padding, 0), 0) # 裁剪掉右侧非因果部分
        self.relu1 = nn.ReLU()
        self.dropout1 = nn.Dropout(dropout)

        # 第二层膨胀因果卷积
        self.conv2 = weight_norm(nn.Conv1d(n_outputs, n_outputs, kernel_size,
                                           stride=stride, padding=padding, dilation=dilation))
        self.chomp2 = nn.ConstantPad1d((-padding, 0), 0)
        self.relu2 = nn.ReLU()
        self.dropout2 = nn.Dropout(dropout)

        self.net = nn.Sequential(self.conv1, self.chomp1, self.relu1, self.dropout1,
                                 self.conv2, self.chomp2, self.relu2, self.dropout2)
        
        # 残差连接：如果输入输出维度不一致，使用 1x1 卷积对齐
        self.downsample = nn.Conv1d(n_inputs, n_outputs, 1) if n_inputs != n_outputs else None
        self.relu = nn.ReLU()

    def forward(self, x):
        out = self.net(x)
        res = x if self.downsample is None else self.downsample(x)
        return self.relu(out + res)

class TCNModel(nn.Module):
    def __init__(self, input_size, output_size, num_channels, kernel_size=3, dropout=0.2):
        super(TCNModel, self).__init__()
        layers = []
        num_levels = len(num_channels)
        for i in range(num_levels):
            dilation_size = 2 ** i
            in_channels = input_size if i == 0 else num_channels[i-1]
            out_channels = num_channels[i]
            layers += [ChainedCausalConv(in_channels, out_channels, kernel_size, stride=1, dilation=dilation_size,
                                         padding=(kernel_size-1) * dilation_size, dropout=dropout)]

        self.tcn = nn.Sequential(*layers)
        self.linear = nn.Linear(num_channels[-1], output_size)

    def forward(self, x):
        # x 形状: (Batch, Features, Seq_Length)
        y1 = self.tcn(x)
        # 取最后一个时间步的特征进行预测
        return self.linear(y1[:, :, -1])

# ======================== 2. 策略初始化与执行 ========================
def initialize(context):
    set_benchmark('000905.XSHG')
    set_option('use_real_price', True)
    set_order_cost(OrderCost(close_tax=0.001, open_commission=0.0003, close_commission=0.0003, min_commission=5), type='stock')
    
    # 策略参数
    g.stock_num = 10
    g.seq_length = 30           # 观察过去 30 天
    g.feature_num = 6           # 特征数: OHLCV + MarketCap
    
    # 初始化模型
    # 通道数设计：[16, 32, 64] 代表 3 层残差块
    g.model = TCNModel(input_size=g.feature_num, output_size=1, num_channels=[16, 32, 64])
    g.model.eval() # 开启推理模式
    
    # 注意：在真实实盘中，这里应该加载训练好的权重文件
    # torch.load(get_file_path('tcn_weights.pth'))
    # 1. 实例化未经训练的模型结构
    g.model = TCNModel(input_size=g.feature_num, output_size=1, num_channels=[16, 32, 64])
    
    # ==========================================
    # 用以下这段替换掉原本报错的那行 torch.load
    # ==========================================
    # 1. 调用聚宽 API 读取研究环境文件，获得二进制内存流
    file_bytes = read_file('tcn_classification_weights.pth')
    
    # 2. 将二进制流转化为 BytesIO 对象，模拟文件句柄
    buffer = io.BytesIO(file_bytes)
    
    # 3. 让 PyTorch 从内存流中加载权重
    g.model.load_state_dict(torch.load(buffer))
    # ==========================================
    
    # 锁定权重，开启推理模式
    g.model.eval() 
        # 定期执行
    run_monthly(rebalance, monthday=1, time='09:30')

def get_prepared_tensor(stock, seq_length):
    """提取单只股票的特征并转化为 Tensor (1, Features, Seq)"""
    hist = attribute_history(stock, seq_length, '1d', ['open', 'close', 'high', 'low', 'volume', 'money'], df=False)
    
    # 构建矩阵
    data = np.array([hist['open'], hist['close'], hist['high'], hist['low'], hist['volume'], hist['money']])
    
    # Z-Score 标准化 (在时间轴上)
    mean = np.mean(data, axis=1, keepdims=True)
    std = np.std(data, axis=1, keepdims=True) + 1e-8
    norm_data = (data - mean) / std
    
    # 转化为 Tensor 并增加 Batch 维度: (1, F, T)
    return torch.tensor(norm_data, dtype=torch.float32).unsqueeze(0)

def rebalance(context):
    # 1. 择时逻辑 (保留之前的 MA60 盾牌)
    hist_index = attribute_history('000300.XSHG', 60, '1d', ['close'])
    if hist_index['close'][-1] < hist_index['close'].mean():
        print("大盘走弱，TCN 策略转入防守空仓。")
        for stock in context.portfolio.positions:
            order_target_value(stock, 0)
        return

    # 2. 选股池过滤：基本面硬条件 (ROE > 5, ROA > 3)
    all_stocks = list(get_all_securities(['stock']).index)
    current_data = get_current_data()
    
    # 初筛：小市值 + 质量指标
    q = query(valuation.code).filter(
        valuation.code.in_(all_stocks),
        indicator.roe > 5.0,
        indicator.roa > 3.0
    ).order_by(valuation.market_cap.asc()).limit(150) # 先取前 150 名进入 TCN 评分
    
    candidate_pool = [s.code for s in get_fundamentals(q).itertuples() 
                      if not current_data[s.code].is_st and not current_data[s.code].paused]

    # 3. TCN 预测评分
    scores = {}
    with torch.no_grad():
        for stock in candidate_pool:
            try:
                # 获取该股票的历史张量
                x = get_prepared_tensor(stock, g.seq_length)
                # 模型预测（输出预测收益率评分）
                pred_score = g.model(x).item()
                scores[stock] = pred_score
            except:
                continue
    
    # 按预测分数从高到低排序，选前 N 只
    final_buy_list = sorted(scores, key=scores.get, reverse=True)[:g.stock_num]
    
    # 4. 执行调仓
    for stock in context.portfolio.positions:
        if stock not in final_buy_list:
            order_target_value(stock, 0)
            
    if final_buy_list:
        target_value = context.portfolio.total_value / len(final_buy_list)
        for stock in final_buy_list:
            order_target_value(stock, target_value)