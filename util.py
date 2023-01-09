import os
import configparser

ROOT_DIR = os.path.dirname(os.path.realpath(__file__))
MAX_DEBUG_ARTIFACTS = 100

def GetConfig(option: str):
    """Returns (score, rarity) threshold."""
    cfg = configparser.ConfigParser()
    cfg.read(os.path.join(ROOT_DIR, 'config', 'screen.ini'))
    return float(cfg.get('screen', option))




if __name__ == '__main__':
    print('---debugging---')
    # print(ROOT_DIR)
    # print(os.path.curdir)
    print(GetConfig('abc'))