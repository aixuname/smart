# 第 5 周：NumPy 基础

> 配套代码：[ch10_numpy入门.py](../Python基础/ch10_numpy入门.py)

[讲义目录](./README.md) · [← 上一周：第 4 周](./第04周_文件异常与类.md) · [下一周：第 6 周 →](./第06周_Pandas基础.md)

## 本周目标

学完这一周，你应该能：

- 说清「列表能做的，为什么还要用 NumPy 数组」。
- 熟练创建数组，看懂 `shape`、`dtype`。
- 用切片、布尔索引取出想要的数据。
- 对整组数据做运算，不用写循环。
- 用 `axis` 参数计算「按行」「按列」的统计。
- **本周产出**：用 NumPy 做一次成绩统计。

---

## 一、为什么需要 NumPy

先看一个例子：给 100 万个数各加 1。

```python
# 用列表：只能循环，慢
scores = [90, 85, 77]
new = []
for s in scores:
    new.append(s + 1)

# 用 NumPy：直接加，快
import numpy as np
scores = np.array([90, 85, 77])
new = scores + 1        # 一行搞定
```

NumPy 的两个核心优势：

1. **不用写循环**——对整组数据直接运算（叫「向量化」）。
2. **快**——底层是 C 写的，数据量越大差距越明显。后面的 Pandas、PyTorch 全都建立在它上面。

> 装好 NumPy 了吗？没装的运行 `pip install numpy`。Anaconda 里自带，一般不用装。

## 二、创建数组

```python
import numpy as np

# 从列表创建
a = np.array([1, 2, 3, 4, 5])
b = np.array([[1, 2, 3],
              [4, 5, 6]])       # 二维数组（矩阵）

# 自动生成
print(np.arange(5))              # [0 1 2 3 4]        类似 range，不含尾
print(np.arange(1, 10, 2))       # [1 3 5 7 9]        带步长
print(np.linspace(0, 1, 5))      # [0. 0.25 0.5 0.75 1.]  均分 5 个点

# 特殊数组
print(np.zeros(3))               # [0. 0. 0.]
print(np.ones((2, 3)))           # 2 行 3 列全是 1
print(np.full(3, 7))             # [7 7 7]
print(np.eye(3))                 # 3x3 单位矩阵

# 随机数
print(np.random.rand(3))         # 3 个 0~1 的随机小数
print(np.random.randint(0, 100, 5))   # 5 个 0~99 的随机整数
print(np.random.randn(3))        # 标准正态分布
```

> 固定随机结果方便对照：`np.random.seed(42)` 放在生成随机数之前。

## 三、数组的属性

```python
a = np.array([[1, 2, 3],
              [4, 5, 6]])

print(a.shape)     # (2, 3)     2 行 3 列
print(a.ndim)      # 2          维度数
print(a.size)      # 6          元素总数
print(a.dtype)     # int64      数据类型
```

`shape` 是最重要的属性，**后面 90% 的报错都和 shape 对不上有关**。

类型转换：

```python
print(np.array([1, 2, 3], dtype=float))   # [1. 2. 3.]
print(a.astype(float))
```

## 四、索引与切片

和列表类似，但**多维数组可以一次取一个区域**。

```python
a = np.array([10, 20, 30, 40, 50])

print(a[0])        # 10
print(a[-1])       # 50
print(a[1:4])      # [20 30 40]     含头不含尾
print(a[::2])      # [10 30 50]     步长 2
```

二维数组用 `[行, 列]`，逗号分隔：

```python
m = np.array([[1, 2, 3],
              [4, 5, 6],
              [7, 8, 9]])

print(m[0, 0])      # 1      第 0 行第 0 列
print(m[1])         # [4 5 6]        整行
print(m[:, 0])      # [1 4 7]        整列（: 表示这一维全要）
print(m[0:2, 1:3])  # [[2 3] [5 6]]  左上角 2x2 区域
```

> 二维数组的读法：`[行的范围, 列的范围]`。冒号 `:` 就是「全都要」。

## 五、布尔索引（最好用的技巧）

```python
scores = np.array([90, 85, 77, 92, 60, 45, 88])

mask = scores >= 80          # [ True  True False  True False False  True]
print(scores[mask])          # [90 85 92 88]     只取出符合条件的

print(scores[scores < 60])   # [45]
```

比写循环加 `if` 简洁得多。以后 Pandas 的筛选也是这个思路。

组合条件用 `&`（且）、`|`（或），**每个条件都要加括号**：

```python
print(scores[(scores >= 60) & (scores < 90)])   # [85 77 60 88]
print(scores[(scores < 60) | (scores >= 90)])   # [90 92 45]
```

> `and` / `or` 在这里不能用，必须用 `&` / `|`。这是新手必踩的坑。

## 六、数组运算与广播

### 1. 整组一起算

```python
a = np.array([1, 2, 3])
b = np.array([10, 20, 30])

print(a + b)       # [11 22 33]     对应位置相加
print(a * 2)       # [2 4 6]        每个都乘
print(a ** 2)      # [1 4 9]
print(a > 1)       # [False  True  True]
```

### 2. 广播：shape 不一样也能算

```python
scores = np.array([[90, 85, 77],
                   [60, 70, 80]])       # 2 个学生 3 门课

bonus = np.array([5, 5, 5])             # 每门课加 5 分
print(scores + bonus)                   # 会自动套用到每一行

print(scores + 5)                       # 标量也行
print(scores.mean(axis=1))              # 每个学生的平均分
```

## 七、统计函数与 axis

```python
scores = np.array([[90, 85, 77],
                   [60, 70, 80],
                   [95, 88, 92]])

print(scores.sum())            # 总分
print(scores.mean())           # 全体平均
print(scores.max(), scores.min())
print(scores.std())            # 标准差

print(scores.mean(axis=0))     # 按列（每个学生）计算 → [81.67 81. 83.]
print(scores.mean(axis=1))     # 按行（每门课）计算 → [...]
```

> **`axis` 记法**：`axis=0` 是「沿着行往下压」，结果按列；`axis=1` 是「沿着列往右压」，结果按行。记不住就先跑一遍看输出形状，很快就有感觉了。

## 八、矩阵运算（为下学期铺垫）

```python
A = np.array([[1, 2],
              [3, 4]])
B = np.array([[5, 6],
              [7, 8]])

print(A * B)      # 对应位置相乘（不是矩阵乘法！）
print(A @ B)      # 矩阵乘法：[[19 22] [43 50]]
print(A.dot(B))   # 同上
print(A.T)        # 转置：[[1 3] [2 4]]
```

> `*` 是逐元素乘，`@` 才是线性代数里的矩阵乘法。下学期神经网络的每一次前向传播都是 `X @ W + b`，所以这两个以后会天天见。

## 九、本周产出：成绩统计

```python
import numpy as np

# 3 个学生，4 门课的成绩
scores = np.array([
    [90, 85, 77, 92],
    [60, 70, 80, 55],
    [95, 88, 92, 78]
])
names = ["小明", "小红", "小刚"]
subjects = ["语文", "数学", "英语", "物理"]

print("整体平均分：", round(scores.mean(), 2))
print("最高分：", scores.max(), " 最低分：", scores.min())

print("\n每个学生的平均分：")
for i, name in enumerate(names):
    print(f"  {name}: {scores[i].mean():.1f}")

print("\n每门课的平均分：")
for i, subject in enumerate(subjects):
    print(f"  {subject}: {scores[:, i].mean():.1f}")

# 每个学生的及格科目数
passed = (scores >= 60).sum(axis=1)
print("\n每人及格科目数：", passed)

# 找出所有不及格的分数
print("不及格的分数：", scores[scores < 60])
```

## 十、常见错误对照表

| 报错 / 现象 | 原因 | 解决 |
| --- | --- | --- |
| `AttributeError: 'list' object has no attribute 'mean'` | 还是 Python 列表，不是数组 | 先 `np.array(...)` 转一下 |
| `ValueError: operands could not be broadcast together` | 两个数组 shape 对不上 | `print(a.shape, b.shape)` 检查 |
| `arrays used as indices must be of integer type` | 索引传了小数 | 索引必须是整数 |
| `TypeError: ufunc 'add' did not contain a loop...` | 数组里混了字符串 | 检查 `dtype`，转成数值 |
| `and` / `or` 用在数组上结果不对 | 应该用 `&` / `|` | 改成位运算符，并给每个条件加括号 |
| `axis=0` 和 `axis=1` 结果反了 | 记混了 | 跑一遍看输出，`axis=0` 压掉行 |
| 打印出来是 `[1. 2. 3.]` 不是 `[1, 2, 3]` | 那是 float 数组 | 正常现象，`.` 表示浮点 |

---

## 十一、课堂练习（45 分钟）

1. **创建与属性**：创建 1~20 的数组，改成 4 行 5 列，输出它的 `shape`、`size`、`dtype`，并取出第 2 行和最后一列。
2. **布尔索引**：给一个 50 个元素的随机整数数组（0~100），取出所有大于 60 的元素，并统计它们的个数。
3. **axis 练习**：造一个 3 行 4 列的随机数组，分别求出按行求和、按列求平均的结果，并说出两者的形状。

## 十二、课后作业

**作业 5.1 班级成绩分析（必做）**

用 `np.random.randint(50, 100, (5, 4))` 生成 5 个学生 4 门课的成绩，完成：

- 输出每个学生的总分和平均分（用 `axis`）。
- 输出每门课的班级平均分。
- 输出班级最高分是哪一位同学、哪一门课。
- 输出全班的不及格率。

**作业 5.2 矩阵运算（必做）**

手动创建矩阵 `X`（3 行 2 列）和权重 `W`（2 行 1 列），计算 `X @ W`，说出结果的形状。然后把 `W` 变成 2 行 3 列再算一次，观察结果的变化。

> 这个作业就是下学期线性回归前向传播的雏形，先熟悉一下。

## 十三、自查清单

- [ ] 我能说清 NumPy 数组比列表好在哪两个地方。
- [ ] 我会用 `np.array` / `np.arange` / `np.linspace` / `np.random` 创建数组。
- [ ] 我每次创建完数组都会看一眼 `shape`。
- [ ] 我能用 `[行, 列]` 取出二维数组的整行、整列和一个区域。
- [ ] 我能用布尔索引取出符合条件的元素，并知道要用 `&` `|` 加括号。
- [ ] 我能用 `axis=0` / `axis=1` 区分按列和按行计算。
- [ ] 我分得清 `*`（逐元素）和 `@`（矩阵乘法）。
