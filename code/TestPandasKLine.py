import matplotlib.pyplot as plt
import pandas as pd
from unittest import TestCase
import mplfinance as mpf


class TestPandasKLine(TestCase):
    #读取股票数据：画出k线
    def testKLineChart(self):
        file_name="./demo.csv"
        df = pd.read_csv(file_name)
        df.columns =["Stock_id","Date","Close","Open","High","Low","Volume"]
        df['Date'] = pd.to_datetime(df['Date'])
        df.set_index('Date', inplace=True)

        # 1. 设置市场颜色
        # up='r' (red) 表示涨为红色
        # down='g' (green) 表示跌为绿色
        # edge='i' (inherit) 表示边缘颜色继承 K 线本身的颜色
        # wick='i' 表示影线颜色继承 K 线本身的颜色
        # volume='in' 表示成交量颜色也继承 K 线颜色（涨红跌绿）
        mc = mpf.make_marketcolors(up='red', down='green', edge='i', wick='i', volume='in')

        # 2. 创建样式
        # 基于 'yahoo' 风格进行修改，应用上面定义的市场颜色
        s = mpf.make_mpf_style(marketcolors=mc, gridstyle='--', y_on_right=False)

        mpf.plot(df, type='candle', style=s, title='Stock Price', volume=False, datetime_format='%Y-%m-%d')
        plt.show()



    #K线带交易量
    def testKLineByVolume(self):
        file_name="./demo.csv"
        df = pd.read_csv(file_name)
        df.columns =["Stock_id","Date","Close","Open","High","Low","Volume"]
        df['Date'] = pd.to_datetime(df['Date'])
        df.set_index('Date', inplace=True)

        mc = mpf.make_marketcolors(up='red', down='green', edge='i', wick='i', volume='in')
        s= mpf.make_mpf_style(marketcolors=mc, gridstyle='--', y_on_right=False)

        mpf.plot(df, type='candle', style=s, title='Stock Price', volume=True, datetime_format='%Y-%m-%d')

    # K线带交易量与均线
    def testKLineByMA(self):
        file_name="./demo.csv"
        df = pd.read_csv(file_name)
        df.columns =["Stock_id","Date","Close","Open","High","Low","Volume"]
        df['Date'] = pd.to_datetime(df['Date'])
        df.set_index('Date', inplace=True)
        mc = mpf.make_marketcolors(up='red', down='green', edge='i', wick='i', volume='in')
        s= mpf.make_mpf_style(marketcolors=mc, gridstyle='--', y_on_right=False)
        mpf.plot(df, type='candle', style=s, title='Stock Price', volume=True, datetime_format='%Y-%m-%d', mav=(5, 10, 20))