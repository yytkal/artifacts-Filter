from configparser import ConfigParser
import util

import pandas as pd

from artifact import Artifact, artifacts, good_arts
from build import build_df

# 根据不同部位觉得适配度评分（略微降低要求）。
# 详情见https://nga.178.com/read.php?tid=33747478，排序筛选
# 3 对应大毕业
# 2 对应小毕业
# 1 对应新手/摆烂
score_threshold = util.GetConfig('score_threshold')
_PER_POSITION_SCORE_THRESHOLD = {
    'flower': {
        3: 85,
        2: 75,
        1: 40
    },
    'feather': {
        3: 85,
        2: 75,
        1: 40
    },
    'sand': {
        3: 75,
        2: 65,
        1: 50
    },
    'head': {
        3: 75,
        2: 65,
        1: 50
    },
    'cup': {
        3: 65,
        2: 50,
        1: 30
    },
}
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
    "sand": 0.5,
    "cup": 0.0,
    "head": 0.5,
}


def adapt(art: Artifact, df: pd.DataFrame):
    """对每一个build进行适配性评分"""
    d_temp = {}
    p = 0
    best_score = 0
    for k in range(df.shape[1]):  # 遍历build库
        current_build = df[k]
        fitness = 0  # 对该build的适配度
        build_adapt = pd.Series([], dtype='float64')
        num_upgrades = int(art.level / 4)
        lvl_0_main_fitness = art.main.multiply(current_build['{}MainWeights'.format(art.position)]).dropna().sum()  # 主属性加权和
        main_fitness_gain_per_upgrade = lvl_0_main_fitness / 4.0  # 主属性fitness随着等级提升，从而防止副属性得分占比过高。
        fitness += lvl_0_main_fitness + main_fitness_gain_per_upgrade * num_upgrades
        fitness += art.sec.multiply(current_build['secWeights']).dropna().sum()  # 副属性加权和
        if art.set not in current_build['sets']:  # 非对应套装，依据部位减去一定的适配度评分
            lvl_0_fitness_sub = fitness_sub[art.position]
            fitness -= lvl_0_fitness_sub * (1 + num_upgrades / 4.0)  # 非套装扣分同样应该根据等级scale
        if art.star < 5:
            raise NotImplemented
        # calculate new best score if already upgraded.
        # 计算方法1：同时scale主属性，并且每次升级都提升最高得副属性，这种方法导致要求过于严格，8词条花不能达到小毕业标准
        # upgraded_best_score = current_build['best_{}'.format(art.position)]
        # if art.position not in ['flower', 'feather']:  # 主属性初始权重为3.5
        #     upgraded_best_score += 3.5 * (num_upgrades / 4.0)
        # upgraded_best_score += num_upgrades * current_build.secWeights.max()
        # 计算方法2：直接将0级best_score根据升级次数scale
        upgraded_best_score = current_build['best_{}'.format(art.position)] * (1 + num_upgrades / 4.0)
        adapt_score = fitness / upgraded_best_score  # 适配分 = 适配度 / 最佳适配度
        # 将build-评分-难度储存到列表中，并以指针为key储存到字典中
        build_adapt['buildName'] = current_build['buildName']
        build_adapt['adaptScore'] = adapt_score
        build_adapt['difficulty'] = current_build['{}Difficulty'.format(art.position)]
        d_temp[p] = build_adapt
        p += 1
    art_adapt = pd.DataFrame(d_temp).T  # 字典压缩成df数据表
    best_score = art_adapt['adaptScore'].max()  # 获得最佳适配度
    # 以适配度为第一优先级、毕业难度为第二优先级对df数据表进行排序
    art_adapt = art_adapt.sort_values(by='adaptScore', ascending=False)
    art_adapt = sort_art(art_adapt)

    print(a.abstract)
    print(a.main_chs)
    print(a.sec_chs)
    print('该圣遗物最佳评分为:【{}】, 稀有度为{}.'.
          format('{:.1%}'.format(best_score),
                 '{:.1f}'.format(a.rarity)))
    print('---------build列表---------')
    temp = art_adapt
    if temp.shape[0] > 10:
        temp = temp.iloc[0:10]
    for j in range(temp.shape[0]):
        print('对BUILD:[{}]的适配度为【{}】,该部位完美毕业难度为: {}'.format(
            temp.iloc[j]['buildName'], '{:.1%}'.format(temp.iloc[j]['adaptScore']),
            '{:.1f}'.format(temp.iloc[j]['difficulty'])))
    # 装入圣遗物评分列表前要先筛选掉不合格的适配评分
    art_adapt = art_adapt[art_adapt['adaptScore'] > _PER_POSITION_SCORE_THRESHOLD[a.position][score_threshold] / 100.0]
    return best_score, art_adapt


if __name__ == '__main__':
    print('正在分析圣遗物......')
    if score_threshold == 3:
        score_cn = '大毕业'
    elif score_threshold == 2:
        score_cn = '小毕业'
    else:
        score_cn = '新手/摆烂'

    print('只上锁适配度为{}, 或稀有度大于{}的圣遗物.'.format(
        score_cn, '{:.1f}'.format(rarity_threshold)))
    if DEBUG:
        print('测试模式，只检测前100个圣遗物.')

    art_d = {}
    p_ = 0
    idx = 0
    lock = [0] * 2000
    num_artifacts = len(artifacts)
    artifacts_to_examine = min(
        util.MAX_DEBUG_ARTIFACTS, num_artifacts) if DEBUG else num_artifacts
    for artifact in artifacts[:artifacts_to_examine]:
        a = Artifact()
        a.read(artifact)
        temp_best = 0
        if a.should_examine():
            if a.rarity > 0:
                print(f'<=========================【圣遗物评测:{idx}】=================================>')
                temp_best, temp_art_df = adapt(a, build_df)
                fitness_threshold = _PER_POSITION_SCORE_THRESHOLD[a.position][score_threshold] / 100.0
                if temp_best > fitness_threshold or a.rarity > rarity_threshold:  # 筛选最佳适配度或稀有度达标的圣遗物
                    print('锁定。。。')
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
                else:
                    print('狗粮。。。')
            else:
                print('稀有度计算出错，圣遗物详情：')
                print(a.abstract)
                print(a.main_chs)
                print(a.sec_chs)
                raise NotImplemented
        idx = idx + 1
    all_score = pd.DataFrame(art_d).T
    if all_score.shape[0] == 0:
        print('未找到符合条件的圣遗物')
        exit(0)
    all_score = all_score.sort_values(by='bestScore', ascending=False)
    # print('共有{}件圣遗物, 显示其中{}件'.format(len(artifacts), all_score.shape[0]))
    # for i in range(all_score.shape[0]):
    #     print('<============================【{}】============================>'.format(i + 1))
    #     ##print('<============================【{}】============================>'.format(i+1))
    #     print(all_score.iloc[i]['index'])
    #     print(all_score.iloc[i]['artAbstract'])
    #     print(all_score.iloc[i]['artMain'])
    #     print(all_score.iloc[i]['artSec'])
    #     print('该圣遗物最佳评分为:【{}】, 稀有度为{}.'.
    #           format('{:.1%}'.format(all_score.iloc[i]['bestScore']),
    #                  '{:.1f}'.format(all_score.iloc[i]['artRarity'])))
    #     print('---------build列表---------')
    #     temp = all_score.iloc[i]['eachScore']
    #     if temp.shape[0] > 10:
    #         temp = temp.iloc[0:10]
    #     for j in range(temp.shape[0]):
    #         print('对BUILD:[{}]的适配度为【{}】,该部位完美毕业难度为: {}'.format(
    #             temp.iloc[j]['buildName'], '{:.1%}'.format(temp.iloc[j]['adaptScore']),
    #             '{:.1f}'.format(temp.iloc[j]['difficulty'])))

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
    already_locked = []
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
            else:
                already_locked.append(idx)
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
    print(f'需要加锁good.json以下圣遗物(共{len(list_lock)}个)')
    print(f'检测顺序：{lock}')
    print(f'背包顺序：{list_lock}')
    print(f'已锁定:{already_locked}')
