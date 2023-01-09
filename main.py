from configparser import ConfigParser
import util

import pandas as pd

from artifact import Artifact, artifacts, good_arts
from build import build_df


score_threshold = util.GetConfig('score_threshold')
rarity_threshold = util.GetConfig('rarity_threshold')
DEBUG = util.GetConfig('debug')


def sort_art(df: pd.DataFrame):
    k = 0  #
    sorted_df = df.iloc[0:1]
    while k != df.shape[0] - 1:
        for t in range(k, df.shape[0]):
            if t < df.shape[0]:
                if df.iloc[t]['adaptScore'] != df.iloc[k]['adaptScore']:
                    p = t - k  # 切片长度
                    slice_sort = df.iloc[k:k + p]
                    slice_sort = slice_sort.sort_values(by='difficulty', ascending=False)
                    sorted_df = pd.concat([sorted_df, slice_sort])
                    k = t  # 下一次起点
            else:
                if df.iloc[t]['adaptScore'] == df.iloc[k]['adaptScore']:
                    p = t - k + 1  # 切片长度
                    slice_sort = df.iloc[k:k + p]
                    slice_sort = slice_sort.sort_values(by='difficulty', ascending=False)
                    sorted_df = pd.concat([sorted_df, slice_sort])
                    k = t  # 最终的终点
        break
    sorted_df = sorted_df[1:]
    return sorted_df


fitness_sub = {
    "flower": 1,
    "feather": 1,
    "sand": 0.8,
    "cup": 0.6,
    "head": 0.8,
}


def adapt(art: Artifact, df: pd.DataFrame):
    """对每一个build进行适配性评分"""
    d_temp = {}
    p = 0
    best_score = 0
    for k in range(df.shape[1]):  # 遍历build库
        fitness = 0  # 对该build的适配度
        build_adapt = pd.Series([], dtype='float64')
        fitness += art.main.multiply(df[k]['{}MainWeights'.format(art.position)]).dropna().sum()  # 主属性加权和
        fitness += art.sec.multiply(df[k]['secWeights']).dropna().sum()  # 副属性加权和
        if art.set not in df[k]['sets']:  # 非对应套装，依据部位减去一定的适配度评分
            fitness -= fitness_sub[art.position]
        if art.star < 5:  # 非五星扣0.6
            # fitness -= 0.6
            raise NotImplemented
        adapt_score = fitness / df[k]['best_{}'.format(art.position)]  # 适配分 = 适配度 / 最佳适配度
        # 将build-评分-难度储存到列表中，并以指针为key储存到字典中
        build_adapt['buildName'] = df[k]['buildName']
        build_adapt['adaptScore'] = adapt_score
        build_adapt['difficulty'] = df[k]['{}Difficulty'.format(art.position)]
        d_temp[p] = build_adapt
        p += 1
    art_adapt = pd.DataFrame(d_temp).T  # 字典压缩成df数据表
    best_score = art_adapt['adaptScore'].max()  # 获得最佳适配度
    # 以适配度为第一优先级、毕业难度为第二优先级对df数据表进行排序
    art_adapt = art_adapt.sort_values(by='adaptScore', ascending=False)
    art_adapt = sort_art(art_adapt)
    # 装入圣遗物评分列表前要先筛选掉不合格的适配评分
    art_adapt = art_adapt[art_adapt['adaptScore'] > score_threshold]
    return best_score, art_adapt


if __name__ == '__main__':
    print('正在分析圣遗物......')
    print('只显示适配度大于{}, 或稀有度大于{}的圣遗物.'.format(
        '{:.1%}'.format(score_threshold), '{:.1f}'.format(rarity_threshold)))
    if DEBUG:
        print('测试模式，只检测前100个圣遗物.')

    art_d = {}
    p_ = 0
    idx = 0
    lock = [0] * 2000
    num_artifacts = len(artifacts)
    # print('比较莫娜，good：',len(artifacts), len(good_arts))
    # print('mona:', artifacts[0])
    # print('locked:', good_arts[0])
    # exit(1)
    artifacts_to_examine = min(
        util.MAX_DEBUG_ARTIFACTS, num_artifacts) if DEBUG else num_artifacts
    for artifact in artifacts[:artifacts_to_examine]:
        a = Artifact()
        a.read(artifact)
        temp_best = 0
        if a.rarity > 0:
            temp_best, temp_art_df = adapt(a, build_df)
            if temp_best > score_threshold or a.rarity > rarity_threshold:  # 筛选最佳适配度或稀有度达标的圣遗物
                art_score = pd.Series([], dtype='float64')
                art_score['artAbstract'] = a.abstract
                art_score['artMain'] = a.main_chs
                art_score['artSec'] = a.sec_chs
                art_score['artRarity'] = a.rarity
                art_score['bestScore'] = temp_best
                art_score['eachScore'] = temp_art_df
                art_score['index'] = idx
                lock[idx] = 1
                art_d[p_] = art_score
                p_ += 1
        idx = idx + 1
    all_score = pd.DataFrame(art_d).T
    all_score = all_score.sort_values(by='bestScore', ascending=False)
    print('共有{}件圣遗物, 显示其中{}件'.format(len(artifacts), all_score.shape[0]))
    for i in range(all_score.shape[0]):
        print('<============================【{}】============================>'.format(i + 1))
        ##print('<============================【{}】============================>'.format(i+1))
        print(all_score.iloc[i]['index'])
        print(all_score.iloc[i]['artAbstract'])
        print(all_score.iloc[i]['artMain'])
        print(all_score.iloc[i]['artSec'])
        print('该圣遗物最佳评分为:【{}】, 稀有度为{}.'.
              format('{:.1%}'.format(all_score.iloc[i]['bestScore']),
                     '{:.1f}'.format(all_score.iloc[i]['artRarity'])))
        print('---------build列表---------')
        temp = all_score.iloc[i]['eachScore']
        if temp.shape[0] > 10:
            temp = temp.iloc[0:10]
        for j in range(temp.shape[0]):
            print('对BUILD:[{}]的适配度为【{}】,该部位完美毕业难度为: {}'.format(
                temp.iloc[j]['buildName'], '{:.1%}'.format(temp.iloc[j]['adaptScore']),
                '{:.1f}'.format(temp.iloc[j]['difficulty'])))

    idx = 0
    plume = 0  ##羽
    sands = 0  ##沙
    flower = 0  ##花
    circlet = 0  ##头
    goblet = 0  ##杯
    idx_convert = 0
    for good_art in good_arts:
        if (good_art['slotKey'] == 'flower'):
            flower = flower + 1
        if (good_art['slotKey'] == 'plume'):
            plume = plume + 1
        if (good_art['slotKey'] == 'sands'):
            sands = sands + 1
        if (good_art['slotKey'] == 'goblet'):
            goblet = goblet + 1
        if (good_art['slotKey'] == 'circlet'):
            circlet = circlet + 1
    bias_flower = 0
    bias_plume = flower
    bias_sands = flower + plume
    bias_goblet = flower + plume + sands
    bias_circlet = flower + plume + sands + goblet

    plume = 0  ##羽
    sands = 0  ##沙
    flower = 0  ##花
    circlet = 0  ##头
    goblet = 0  ##杯
    idx_convert = 0
    list_lock = []
    for good_art in good_arts:
        ##a.read(good_art)
        ##a.read(good_art)

        ##print( good_art['slotKey'])
        if (good_art['slotKey'] == 'flower'):
            idx_convert = bias_flower + flower
            flower = flower + 1
        if (good_art['slotKey'] == 'plume'):
            idx_convert = bias_plume + plume
            plume = plume + 1
        if (good_art['slotKey'] == 'sands'):
            idx_convert = bias_sands + sands
            sands = sands + 1
        if (good_art['slotKey'] == 'goblet'):
            idx_convert = bias_goblet + goblet
            goblet = goblet + 1
        if (good_art['slotKey'] == 'circlet'):
            idx_convert = bias_circlet + circlet
            circlet = circlet + 1
            ##print('circlet+1')
        ##idx_convert = flower+plume+sands+goblet+circlet
        if (lock[idx_convert] == 1):
            ##print( good_art)
            if (good_art['lock'] == False):
                list_lock.append(idx)
            # TODO: Make sure mona and good are matched correctly.
            try:
                mona_art = artifacts[idx_convert]
                lock_art = good_arts[idx]
                # 比较主属性以及等级，套装等信息
                # assert mona_art['setName'].lower() == lock_art['setKey'].lower()
                # assert mona_art['position'] == lock_art['slotKey']
                assert mona_art['level'] == lock_art['level']
                assert mona_art['star'] == lock_art['rarity']
                # todo: 比较属性值
            except:
                print('圣遗物匹配失败，放弃锁定。检查mona.json与good.json格式是否改动:')
                print(f'mona.json: {mona_art}')
                print(f'good.json: {lock_art}')
                raise
            ##print('<============mona==============【{}】============================>'.format(idx_convert))
            ##print('<============good================【{}】============================>'.format(idx))
        idx += 1
    print_lock = open("lock.json", 'w')
    print(list_lock, file=print_lock)
    print_lock.close()
    print('需要加锁good.json以下圣遗物')
    print(list_lock)
