import pandas as pd
import matplotlib.pyplot as plt
from matplotlib import colors as mycolors
from matplotlib.collections import LineCollection,PolyCollection

from unittest import TestCase

from matplotlib.lines import lineStyles


class   TestMACD(TestCase):
    def cal_macd(self,df,fastperiod=12,slowperiod=26,signalperiod=9):
        ewma12= df['Close'].ewm(span=fastperiod,adjust=False).mean()
        ewma26= df['Close'].ewm(span=slowperiod,adjust=False).mean()
        df['dif']=ewma12-ewma26
        df['dea']=df['dif'].ewm(span=signalperiod,adjust=False).mean()
        df['bar']=2*(df['dif']-df['dea'])
        return df
    def testMACD(self):
        file_name="./demo.csv"
        df = pd.read_csv(file_name)
        df.columns =["Stock_id","Date","Close","Open","High","Low","Volume"]
        df=df[["Date","Close","Open","High","Low","Volume"]]
        df['Date'] = pd.to_datetime(df['Date'])
        ##df.set_index('Date', inplace=True)

        df_macd=self.cal_macd(df)
        print(df_macd)

        plt.figure(figsize=(12,8))
        df_macd['dea'].plot(color="red",label='dea')
        df_macd['dif'].plot(color="blue",label='dif')
        plt.legend(loc='best')

        pos_bar=[]
        pos_index=[]
        neg_bar=[]
        neg_index=[]

        for index,row in df_macd.iterrows():
            if row['bar']>0:
                pos_bar.append(row['bar'])
                pos_index.append(index)
            else:
                neg_bar.append(row['bar'])
                neg_index.append(index)


        #大于0用红色表示
        plt.bar(pos_index,pos_bar,width=0.5,color='r')
        #小于0用绿色表示
        plt.bar(neg_index,neg_bar,width=0.5,color='g')

        major_index = df_macd.index[df_macd.index]
        major_xtics =df_macd['Date'][df_macd.index]
        plt.xticks(major_index,major_xtics)
        plt.setp(plt.gca().get_xticklabels(), rotation=30, horizontalalignment='right')

        plt.grid(linestyle='-.')
        plt.title('000001平安银行MACD图')
        plt.rcParams['axes.unicode_minus'] = False
        plt.rcParams['font.sans-serif']=['SimHei'] #用来正常显示中文标签

        plt.show()