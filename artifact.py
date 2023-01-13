import json
import os

import pandas as pd
from jsonpath import jsonpath

import util
from dict import set_dict, attribute_dict, position_dict
from rarity import rarity

_MAX_LVL = int(util.GetConfig('max_artifact_lvl'))
_MIN_LVL = int(util.GetConfig('min_artifact_lvl'))
proDir = os.path.split(os.path.realpath(__file__))[0]

with open(proDir + '/mona.json', 'r', encoding='utf8') as jd:
    art_data = json.load(jd)
with open(proDir + '/good.json', 'r', encoding='utf8') as gd:
    lock_data = json.load(gd)

good_arts = jsonpath(lock_data, "$.artifacts[*]")
artifacts = jsonpath(art_data, "$.flower[*]") + jsonpath(art_data, "$.feather[*]") + \
            jsonpath(art_data, "$.sand[*]") + jsonpath(art_data, "$.cup[*]") + jsonpath(art_data, "$.head[*]")
positions = ['flower', 'feather', 'sand', 'cup', 'head']


class Artifact:
    def __init__(self):
        self.abstract = None
        self.star = None
        self.set = None
        self.set_chs = None
        self.position = None
        self.position_chs = None
        self.level = None
        self.main = pd.Series([], dtype='float64')
        self.raw_sec = pd.Series([], dtype='float64')
        self.main_chs = None
        self.sec_chs = None
        self.sec = pd.Series([], dtype='float64')  # 副词条归一化
        self.rarity = 0

    def should_examine(self):
        return _MAX_LVL >= self.level >= _MIN_LVL and self.star >= 4

    def read(self, art_dict: dict):
        self.star = art_dict['star']
        self.set = art_dict['setName']
        self.set_chs = jsonpath(set_dict, "$.{}".format(self.set))[0]["chs"]
        self.position = art_dict['position']
        self.position_chs = position_dict[self.position]
        self.level = art_dict['level']
        self.abstract = '{}星 {} {}; 等级:{}'.format(self.star, self.set_chs, self.position_chs, self.level)
        self.main[jsonpath(art_dict, "$.mainTag.name")[0]] = 1
        self.raw_sec = pd.Series(jsonpath(art_dict, "$.normalTags[*].value"),
                                 index=jsonpath(art_dict, "$.normalTags[*].name"))
        self.main_chs = '主属性为:' + '【{}】'.format(jsonpath(attribute_dict, "$.{}.chs".format(self.main.index[0]))[0])
        sec_index = []
        for i in range(len(self.raw_sec.index.tolist())):
            sec_index += [jsonpath(attribute_dict, "$.{}.chs".format(self.raw_sec.index[i]))[0]]
        temp_sec_chs = pd.Series(self.raw_sec.values, index=sec_index)
        self.sec_chs = '副属性为: '
        for i in range(len(temp_sec_chs)):
            if temp_sec_chs[i] < 1:
                self.sec_chs += '{}--{}; '.format(temp_sec_chs.index[i], '{:.1%}'.format(temp_sec_chs[i]))
            else:
                self.sec_chs += '{}--{}; '.format(temp_sec_chs.index[i], '{:.0f}'.format(temp_sec_chs[i]))
        for i in range(len(self.raw_sec)):
            self.sec[self.raw_sec.index[i]] = \
                self.raw_sec[i] / jsonpath(attribute_dict, "$.{}.average".format(self.raw_sec.index[i]))[0]
        if _MAX_LVL >= self.level >= _MIN_LVL and self.star >= 4:  # 筛选合格的胚子
            if self.star == 4:
                raise NotImplemented
            num_upgrades = int(self.level / 4)
            if self.level < 4:  # 4 级以下可以直接计算稀有度
                rarity_list = [self.position, len(self.sec)] + self.main.index.tolist() + self.sec.index.tolist()
                self.rarity = rarity(rarity_list)
            else:
                total_sec = sum(self.sec)
                self.sec_chs += f'; 现词条数： {total_sec}; '
                estimated_initial_sec_count = total_sec - num_upgrades
                initial_sec_count = 4 if estimated_initial_sec_count >= 3.5 else 3
                self.sec_chs += f'; 初始词条数： {initial_sec_count}; '
                rarity_list = [self.position, initial_sec_count] + self.main.index.tolist() + self.sec.index.tolist()
                self.rarity = rarity(rarity_list)
            # 如果双爆词条数量等于升级数+1，可以留下来当散件
            crit_counts = self.sec.get('critical', 0) + self.sec.get('criticalDamage', 0)
            if self.level >= 4:
                if crit_counts > num_upgrades + 0.5:
                    # 满级圣遗物有5.5条双爆可以留
                    self.rarity = 8.6
                elif self.position == 'head' and self.main.index in (
                        'critical', 'criticalDamage') and crit_counts > num_upgrades / 2:
                    # 满级双爆头有2.5条双爆属性可以留
                    self.rarity = 8.6
            elif (self.position == 'head' and crit_counts > 0.5) or crit_counts > 1.5:
                self.rarity = 8.6


if __name__ == '__main__':
    pass
