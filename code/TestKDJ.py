import pandas as pd
import matplotlib.pyplot as  plt


from unittest import TestCase

from astropy.version import major


class TestKDJ(TestCase):
    def cal_kdj(self,df):
        low_list =df['Low'].rolling(9,min_periods=9).min()
        low_list.fillna(value=df['Low'].expanding().min(), inplace=True)
        high_list =df['High'].rolling(9,min_periods=9).max()
        high_list.fillna(value=df['High'].expanding().max(), inplace=True)
        rsv = (df['Close'] - low_list) / (high_list - low_list) * 100
        df['K'] = pd.DataFrame(rsv).ewm(com=2).mean()
        df['D'] = df['K'].ewm(com=2).mean()
        df['J'] = 3 * df['K'] - 2 * df['D']
        return df
    def test_KDJ(self):
        file_name="./demo.csv"
        df = pd.read_csv(file_name)
        df.columns =["Stock_id","Date","Close","Open","High","Low","Volume"]
        df=df[["Date","Close","Open","High","Low","Volume"]]
        df['Date'] = pd.to_datetime(df['Date'])

        df_kdj=self.cal_kdj(df)
        print(df_kdj)


        plt.figure(figsize=(12,8))
        df_kdj['K'].plot(color="red",label='K')
        df_kdj['D'].plot(color="blue",label='D')
        df_kdj['J'].plot(color="green",label='J')
        plt.legend(loc='best')


        major_index=df_kdj.index[df_kdj.index]
        major_xtics=df_kdj['Date'][df_kdj.index]
        plt.xticks(major_index,major_xtics,rotation=45,fontsize=8)
        plt.setp(plt.gca().get_xticklabels(), rotation=30, horizontalalignment='right')

        plt.grid(linestyle='-.')
        plt.title("000001平安银行KDJ图")
        plt.rcParams['axes.unicode_minus'] = False
        plt.rcParams['font.sans-serif'] = ['SimHei']



        plt.show()


