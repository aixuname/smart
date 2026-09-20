# ============================================================
# 第十章：模块与包
# 目标：学会使用别人写好的代码
# ============================================================

# ---- 1. 导入模块 ----
# 模块就是一个 .py 文件，里面装了一堆现成的功能
# import 用来把它引进来

import math          # math 是数学模块（标准库自带）

print(math.pi)            # 圆周率
print(math.sqrt(16))      # 开平方：4.0
print(math.floor(3.9))    # 向下取整：3
print(math.ceil(3.1))     # 向上取整：4

# ---- 2. 从模块导入特定的东西 ----
from math import pow      # 只导入 pow 函数
print(pow(2, 3))          # 2 的 3 次方：8.0

# 用 as 起别名
import random as r        # random 模块，起个短名 r
print(r.randint(1, 100))  # 随机一个 1 到 100 的整数

# ---- 3. 常用标准库 ----
import random
import datetime

# random：随机数
print(random.random())        # 0 到 1 之间的随机小数
print(random.choice([1, 2, 3, 4]))   # 随机选一个

# datetime：日期时间
now = datetime.datetime.now()
print(now.year, now.month, now.day)  # 今天的年月日
print(now.strftime("%Y-%m-%d %H:%M:%S"))  # 格式化成字符串

# os：操作系统相关
import os
print(os.getcwd())       # 当前所在目录
# os.listdir()           # 列出目录下的文件

# ---- 4. 第三方库 ----
# Python 自带的是标准库，第三方库需要先安装
# 在终端执行：pip install 库名
# 例如：pip install requests （用来发网络请求）
