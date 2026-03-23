import numpy as np
import matplotlib
import matplotlib.pyplot as plt
from unittest import TestCase

from anaconda_navigator.utils.url_utils import file_name
from sympy.printing.pretty.pretty_symbology import line_width


class TestNumpyMA(TestCase):
    def testSMA(self):
        file_name ="./demo.csv"
        end_price,volumn=np.loadtxt(
            fname=file_name,
            delimiter=',',
            usecols=(2,6),
            unpack=True
        )

        print(end_price)
        N=5
        weights=np.ones(N)/N
        print(weights)
        sma=np.convolve(weights,end_price)[N-1:-N+1]
        print(sma)
        plt.plot(sma, linewidth=5, label='SMA')
        plt.legend()
        plt.show()

    def testEXP(self):
        x=np.arange(5)
        y=np.arange(10)
        print("x",x)
        print("y",y)
        print("""Exp x:{}""".format(np.exp(x)))
        print("""Exp y:{}""".format(np.exp(y)))
        print(""""Linespace :{}""".format(np.linspace(-1,0,5)))


    def testEMA(self):
        file_name = "./demo.csv"
        end_price, volumn = np.loadtxt(
            fname=file_name,
            delimiter=',',
            usecols=(2, 6),
            unpack=True
        )
        print(end_price)
        N = 5
        weights = np.exp(np.linspace(-1., 0., N))
        weights/= weights.sum()
        print(weights)
        ema=np.convolve(weights,end_price)[N-1:-N+1]
        print(ema)
        ##plt.plot(ema, linewidth=5, label='EMA')
        ##plt.legend()
        ##plt.show()
        t=np.arange(N-1,len(end_price))
        plt.plot(t,end_price[N-1:], lw=1.0)
        plt.plot(t,ema, lw=2.0)
        pl
        plt.show()