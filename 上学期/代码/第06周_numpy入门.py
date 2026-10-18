# ============================================================
# 第 6 周：NumPy 入门
# 目标：学会用 NumPy 处理数组和数值计算
# ============================================================
# NumPy 是 Python 最核心的科学计算库，处理大量数字非常快
# 它最核心的东西是 ndarray（多维数组）

# ---- 0. 安装和导入 ----
# 用 Anaconda 的话，numpy 一般已经装好了
# 没有的话在终端执行：pip install numpy
import numpy as np          # 惯例：导入并起别名 np

# ---- 1. 创建数组 ----
# 用 np.array() 把列表转成数组
arr = np.array([1, 2, 3, 4, 5])
print(arr)                 # [1 2 3 4 5]
print(type(arr))           # <class 'numpy.ndarray'>

# 创建二维数组（矩阵）
arr2d = np.array([[1, 2, 3], [4, 5, 6]])
print(arr2d)

# ---- 2. 了解数组的基本信息 ----
print(arr.shape)     # (5,)  形状：一维，5 个元素
print(arr2d.shape)   # (2, 3) 两行三列
print(arr.dtype)     # int64 数据类型
print(arr.ndim)      # 1 维度数

# ---- 3. 快速生成数组 ----
print(np.zeros(5))            # 5 个 0
print(np.ones(4))             # 4 个 1
print(np.arange(0, 10, 2))    # 0 到 10，步长 2：[0 2 4 6 8]
print(np.linspace(0, 1, 5))   # 0 到 1 之间均匀取 5 个数
print(np.random.rand(3))      # 3 个 0~1 的随机数

# ---- 4. 数组运算（NumPy 的强项）----
# 直接对整个数组做运算，不用写循环！
a = np.array([1, 2, 3])
b = np.array([10, 20, 30])

print(a + b)       # 对应位置相加 [11 22 33]
print(a * 2)       # 每个元素乘 2
print(a ** 2)      # 每个元素平方
print(a > 2)       # 每个元素判断：[False False  True]

# ---- 5. 索引和切片 ----
arr = np.array([10, 20, 30, 40, 50])
print(arr[0])       # 10
print(arr[1:4])     # [20 30 40]（和列表切片一样）

arr2d = np.array([[1, 2, 3], [4, 5, 6]])
print(arr2d[0])        # 第 0 行：[1 2 3]
print(arr2d[1, 2])     # 第 1 行第 2 列：6
print(arr2d[:, 1])     # 所有行的第 1 列：[2 5]（冒号表示全部）

# ---- 6. 常用统计函数 ----
data = np.array([3, 1, 4, 1, 5, 9, 2, 6])
print(data.sum())      # 求和
print(data.mean())     # 平均值
print(data.max())      # 最大值
print(data.min())      # 最小值
print(data.std())      # 标准差

# 二维按轴统计
m = np.array([[1, 2, 3], [4, 5, 6]])
print(m.sum(axis=0))   # 按列求和（纵向）：[5 7 9]
print(m.sum(axis=1))   # 按行求和（横向）：[6 15]

# ---- 7. 布尔筛选 ----
# 用条件直接挑出符合要求的数据
scores = np.array([55, 78, 90, 63, 88, 95])
print(scores[scores >= 60])        # 只保留及格的
print((scores >= 60).sum())        # 及格的人数

# ---- 8. 改变形状 ----
a = np.arange(6)         # [0 1 2 3 4 5]
b = a.reshape(2, 3)      # 改成 2 行 3 列
print(b)

# ---- 小练习 ----
# 用 numpy 快速算 1 到 100 的平均值
nums = np.arange(1, 101)
print("1 到 100 的平均值：", nums.mean())
