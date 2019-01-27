import pandas as pd
import numpy as np
from dateutil.parser import parse
from copy import deepcopy
import dateutil
import datetime

class shelves():
    def __init__(self):
        PATH = r'../阳光乐选/订单明细_上海.xlsx'
        self.sales_list = (pd.read_excel(PATH)).fillna(method='ffill')
        self.sales_list['创建时间'] = (self.sales_list['创建时间'].apply(str)).apply(parse)

        PATH = r'../阳光乐选/2018.01.03导出数据/上海数据/上架数据_上海.xlsx'
        self.up_list = (pd.read_excel(PATH)).fillna(method='ffill')
        self.up_list['上架时间'] = (self.up_list['上架时间'].apply(str)).apply(parse)

        PATH = r'../阳光乐选/2018.01.03导出数据/上海数据/配送列表_上海.xlsx'
        self.check_list = (pd.read_excel(PATH)).fillna(method='ffill')

    def read_sales(self, target_id, good_name=False, start=False, end=False):
        target = self.sales_list[self.sales_list['货架编号'] == target_id]
        if good_name:
            target = target[target['商品明细'] == good_name]
        if start:
            target = target[target['创建时间'] >= start]
        if end:
            target = target[target['创建时间'] <= end]

        return target.reset_index(drop=True)

    def read_check(self, target_id):
        target_corp = self.get_corp_name(target_id)

        target = self.check_list[self.check_list['店铺名称'] == target_corp]
        target2 = self.up_list[self.up_list['所在货架'] == target_id]

        for i in range(target['时间'].shape[0]):
            for new_time, group in target2.groupby(['上架时间']):
                if target['时间'].iloc[i] == str(new_time)[:10]:
                    target['时间'].iloc[i] = new_time
        return target

    def read_ups(self, target_id):
        target = self.up_list[self.up_list['所在货架'] == target_id]
        return target.reset_index(drop=True)

    def get_lost(self, sold_goods, lost_count, lost_value, limit=10):
        lost_good_list = []
        lost_good = []
        critical = 0

        if lost_count == 1:
            # if lost_value in list(sold_goods['price']):
            target = sold_goods[sold_goods['price'] == lost_value]
            critical = 1
            # elif round(lost_value) in sold_goods['price'].apply(round):
            # target = sold_goods[sold_goods['price'].apply(round) == round(lost_value)]
            # else:
            # target = sold_goods[sold_goods['price'] == lost_value]
            all_name = []
            for name in set(target['name']):
                try:
                    all_name = all_name + '/' + name
                except:
                    all_name = name
            try:
                lost_good = [{'name': all_name, 'number': 1, 'value': target['price'].iloc[0]}]
                lost_good_list.append(lost_good)
            except:
                pass

        else:
            count = 0
            for price, price_group in sold_goods.groupby(['price']):

                if price - lost_value > 0:
                    continue

                all_name = []
                for name in set(price_group['name']):
                    try:
                        all_name = all_name + '/' + name
                    except:
                        all_name = name
                    try:
                        target = target[target['name'] != name]
                    except:
                        target = sold_goods[sold_goods['name'] != name]
                try:
                    target = target[target['price'] != price]
                except:
                    target = sold_goods[sold_goods['price'] != price]

                i = 1
                while lost_value - price * i > 0 and i < lost_count and i <= price_group['count'].iloc[0] and len(lost_good_list) < limit:
                    lost_good = [{'name': all_name, 'number': i, 'value': price}]
                    if lost_value - price * i != 0:
                        other_lost_goods, o_critical = self.get_lost(target, lost_count - i, lost_value - price * i, limit=10)

                    # print(lost_count - i)
                    if critical - o_critical == 1:
                        break
                    else:
                        critical = o_critical

                    for idx, other_lost_good in enumerate(other_lost_goods):
                        lost_good = [{'name': all_name, 'number': i, 'value': price}]
                        lost_good_list.append(lost_good + other_lost_good)
                        if idx >= limit - 1:
                            break
                    i = i + 1

        return lost_good_list, critical

    def get_corp_name(self, target_id):
        target_list = self.read_sales(self.sales_list, target_id)
        target_corp = target_list['店铺名称'].iloc[0]
        return target_corp

    def get_lost_by_check(self, target_id):
        target = self.read_check(target_id)

        for i in range(target.shape[0] - 1, 0, -1):
            print('****************************************')
            start_time = target['时间'].iloc[i]
            end_time = target['时间'].iloc[i - 1]
            delta = dateutil.relativedelta.relativedelta(days=5)

            sales = self.read_sales(start=start_time, end=end_time)
            sold_count = int(sales['商品数量'].sum())
            sold_value = round(float(sales['金额'].sum()), 2)

            start_time = str(parse(str(start_time)) - delta)
            print(start_time, end_time)
            sales = self.read_sales(shelve_id=target_id, start=start_time, end=end_time)
            sold_goods = []
            for good, group in sales.groupby(['商品明细']):
                sold_goods.append({'name': good, 'count': int(group['商品数量'].sum()),
                                   'price': round(float(group['金额'].sum()) / int(group['商品数量'].sum()), 2)})
            sold_goods = pd.DataFrame(sold_goods, columns=['name', 'count', 'price'])

            last_time_count = target['货架总数量'].iloc[i]
            last_time_value = round(target['货架总金额'].iloc[i], 2)

            now_count = target['盘点数量'].iloc[i - 1]
            now_value = round(target['盘点金额'].iloc[i - 1], 2)

            lost_count = last_time_count - now_count - sold_count
            lost_value = round(last_time_value - now_value - sold_value, 2)

            if lost_count > 0 and lost_value < 0.3 * sold_value:
                print(lost_count, lost_value)
                starttime = datetime.datetime.now()
                lost_good = self.get_lost(sold_goods, lost_count, lost_value)[0]
                endtime = datetime.datetime.now()
                # print(target.iloc[i-1])
                print(endtime - starttime)
                print(len(lost_good))
                print(lost_good[:3])


def get_lost(sold_goods, lost_count, lost_value, limit=10):
    lost_good_list = []
    lost_good = []
    critical = 0

    if lost_count == 1:
        # if lost_value in list(sold_goods['price']):
        target = sold_goods[sold_goods['price'] == lost_value]
        critical = 1
        # elif round(lost_value) in sold_goods['price'].apply(round):
        # target = sold_goods[sold_goods['price'].apply(round) == round(lost_value)]
        # else:
        # target = sold_goods[sold_goods['price'] == lost_value]
        all_name = []
        for name in set(target['name']):
            try:
                all_name = all_name + '/' + name
            except:
                all_name = name
        try:
            lost_good = [{'name': all_name, 'number': 1, 'value': target['price'].iloc[0]}]
            lost_good_list.append(lost_good)
        except:
            pass

    else:
        count = 0
        for price, price_group in sold_goods.groupby(['price']):

            if price - lost_value > 0:
                continue

            all_name = []
            for name in set(price_group['name']):
                try:
                    all_name = all_name + '/' + name
                except:
                    all_name = name
                try:
                    target = target[target['name'] != name]
                except:
                    target = sold_goods[sold_goods['name'] != name]
            try:
                target = target[target['price'] != price]
            except:
                target = sold_goods[sold_goods['price'] != price]

            i = 1
            while lost_value - price * i > 0 and i < lost_count and i <= price_group['count'].iloc[0] and len(lost_good_list) < limit:
                lost_good = [{'name': all_name, 'number': i, 'value': price}]
                if lost_value - price * i != 0:
                    other_lost_goods, o_critical = get_lost(target, lost_count - i, lost_value - price * i, limit=10)

                # print(lost_count - i)
                if critical - o_critical == 1:
                    break
                else:
                    critical = o_critical

                for idx, other_lost_good in enumerate(other_lost_goods):
                    lost_good = [{'name': all_name, 'number': i, 'value': price}]
                    lost_good_list.append(lost_good + other_lost_good)
                    if idx >= limit - 1:
                        break
                i = i + 1

    return lost_good_list, critical
