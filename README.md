# artifacts-Filter
- 手动pip 安装运行环境，把yas-lock.exe 放在同一目录下。
- 先管理员权限yas-lock.exe，扫描背包
    - 【可选】打开https://ideless.github.io/artifact/ 将需要扫描的胚子解锁后导出
    - 【可选】再次运行yas-lock进行解锁
    - 【可选】运行yas-lock重新扫描
- 运行main.py筛选，然后再运行yas-lock.exe 给未加锁的胚子加锁

# 添加新圣遗物
- dict.py 修改set_dict, set_simple

# 新角色/build
- 导入build.xlsx,修改并export为csv （末尾可能需要加空行）

# TODO
- 支持8-20级圣遗物 【初步完成，需要测试】
- 完善build库 【完成】
- 代码提速

