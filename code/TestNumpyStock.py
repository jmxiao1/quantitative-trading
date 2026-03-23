from unittest import TestCase
import sys
import numpy as np

class TestNumpyStock(TestCase):
#读取文件
    def testReadFile(self):
      file_name = './demo.csv'
      end_price,volumn=np.loadtxt(
         fname=file_name,
         delimiter=',',
         usecols=(2,6),
         unpack=True
      )
      print(end_price)
      print(volumn)

#计算最高和低价
    def testMaxAndMin(self):
      file_name = './demo.csv'
      high_price,low_price=np.loadtxt(
         fname=file_name,
         delimiter=',',
         usecols=(4,5),
         unpack=True
      )
      print("min_price={}".format(low_price.min()))
      print("max_price={}".format(high_price.max()))

#计算极差
    def testPtp(self):
      file_name = './demo.csv'
      high_price,low_price=np.loadtxt(
         fname=file_name,
         delimiter=',',
         usecols=(4,5),
         unpack=True
      )
      print("max-min of high price: {}".format(np.ptp(high_price)))
      print("max-min of low price: {}".format(np.ptp(low_price)))

#计算加权平均价
    def testAVG(self):
      file_name = './demo.csv'
      end_price,volumn=np.loadtxt(
         fname=file_name,
         delimiter=',',
         usecols=(2,6),
         unpack=True
      )

      print("VWAP: {}".format(np.average(end_price,weights=volumn)))
      print("average price: {}".format(np.average(end_price)))


#计算中位数
#收盘价中位数
    def testMedian(self):
      file_name = './demo.csv'
      end_price,volumn=np.loadtxt(
         fname=file_name,
         delimiter=',',
         usecols=(2,6),
         unpack=True
      )

      print("median price: {}".format(np.median(end_price)))

#计算方差
#收盘价方差
    def testVar(self):
      file_name = './demo.csv'
      end_price,volumn=np.loadtxt(
         fname=file_name,
         delimiter=',',
         usecols=(2,6),
         unpack=True
      )
      print("variance of price: {}".format(np.var(end_price)))
      print("var :{}".end_price.var())

# 计算股票收益率、年波动率及月波动率
# 波动率是对价格变动的一种度量，历史波动率可以根据历史价格数据计算出。计算历史波动率时，需要用到对数收益率
# 年波动率等于对数收益率的标准差除以其均值，再乘以交易日的平方根，通常交易日取250天
# 月波动率等于对数收益率的标准差除以其均值，再乘以交易月的平方根。通常交易
    def testVolatility(self):
      file_name = './demo.csv'
      end_price,volumn=np.loadtxt(
         fname=file_name,
         delimiter=',',
         usecols=(2,6),
         unpack=True
      )
      log_return=np.diff(np.log(end_price))
      annual_volatility=(log_return.std()/log_return.mean())*np.sqrt(250)
      monthly_volatility=(log_return.std()/log_return.mean())*np.sqrt(12)
      print("log_return: {}".format(log_return))
      print("annual_volatility: {}".format(annual_volatility))
      print("monthly_volatility: {}".format(monthly_volatility))