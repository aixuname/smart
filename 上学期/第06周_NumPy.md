# 第 6 周：NumPy 基础

> 完整示例代码见文末「附录」

[课程目录](../README_上学期.md) · [← 上一周：第 5 周](./第05周_OpenCode与Agent基础.md) · [下一周：第 7 周 →](./第07周_Pandas基础与进阶.md)

## 本周目标

学完这一周，你应该能：

- 说清「列表能做的，为什么还要用 NumPy 数组」。
- 熟练创建数组，看懂 `shape`、`dtype`。
- 用切片、布尔索引取出想要的数据。
- 对整组数据做运算，不用写循环。
- 用 `axis` 参数计算「按行」「按列」的统计。
- **本周产出**：用 NumPy 做一次成绩统计。

> **代码阅读约定**：先读 `#` 后面的注释，预测输出，再运行验证。数组学习最重要的习惯是：每做一次变形或运算，都检查 `shape` 和 `dtype`。

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

> 装好 NumPy 了吗？在当前环境中运行 `python -m pip install numpy`。Anaconda 常用环境通常已经包含 NumPy；先运行 `python -c "import numpy; print(numpy.__version__)"` 检查，避免重复安装。

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

# 随机数：创建一个独立的随机数生成器
rng = np.random.default_rng(42)       # 42 是种子，便于同学复现相同结果
print(rng.random(3))                  # 3 个 [0, 1) 的随机小数
print(rng.integers(0, 100, size=5))   # 5 个 [0, 100) 的随机整数
print(rng.normal(size=3))             # 3 个标准正态分布随机数
```

`default_rng(42)` 中的 42 叫**随机种子**。同一个种子会得到同一串伪随机数，适合教学和调试；真实抽样时可写 `np.random.default_rng()`。

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

这里可以把数组想成一张表：`shape=(2, 3)` 表示有 2 行、3 列；`ndim=2` 表示需要“行、列”两个坐标才能定位一个元素；`size=6` 等于 `2 × 3`。`dtype` 会因操作系统而显示 `int32` 或 `int64`，两者在本课都属于整数类型，不是报错。

类型转换：

```python
print(np.array([1, 2, 3], dtype=float))   # [1. 2. 3.]
print(a.astype(float))
```

`astype` 默认返回一个新数组，不会偷偷修改 `a`。如果后续计算需要保留小数，应把结果保存下来：`a_float = a.astype(float)`。

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

广播不是“任何形状都能相加”。NumPy 会从两个 `shape` 的**最右边**开始比较，每一维只有三种情况才兼容：两边相等、其中一边是 1、或其中一边不存在。例如 `(2, 3)` 与 `(3,)` 兼容，后者会被当作每行都使用一次；`(2, 3)` 与 `(2,)` 不兼容。

### 3. 切片可能共享原数组

```python
original = np.array([10, 20, 30, 40])
view = original[1:3]   # NumPy 切片通常是“视图”，与原数组共享数据
view[0] = 999          # 修改 view，也会影响 original[1]
print(original)        # [ 10 999  30  40]

safe_copy = original[1:3].copy()  # 需要独立数据时显式复制
safe_copy[0] = 0
print(original)                  # 原数组不再受影响
```

这和 Python 列表切片返回新列表不同，是 NumPy 初学者很容易忽略的地方。

## 七、统计函数与 axis

```python
scores = np.array([[90, 85, 77],
                   [60, 70, 80],
                   [95, 88, 92]])

print(scores.sum())            # 总分
print(scores.mean())           # 全体平均
print(scores.max(), scores.min())
print(scores.std())            # 标准差

print(scores.mean(axis=0))     # 压掉“学生”这一维，得到每门课平均分
print(scores.mean(axis=1))     # 压掉“科目”这一维，得到每个学生平均分
```

> **`axis` 记法**：`axis=0` 是「沿着行往下压」，结果按列；`axis=1` 是「沿着列往右压」，结果按行。记不住就先跑一遍看输出形状，很快就有感觉了。

原数组形状是 `(3, 3)`：

| 表达式 | 被压掉的维度 | 结果含义 | 结果形状 |
| --- | --- | --- | --- |
| `mean(axis=0)` | 第 0 维（学生/行） | 每门课的平均分 | `(3,)` |
| `mean(axis=1)` | 第 1 维（科目/列） | 每个学生的平均分 | `(3,)` |

如果数组是 3 个学生、4 门课的 `(3, 4)`，两种结果形状分别是 `(4,)` 和 `(3,)`。这个方法比死记“横竖”可靠。

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

# 不指定 axis：把全部 12 个成绩一起计算
print("整体平均分：", round(scores.mean(), 2))
print("最高分：", scores.max(), " 最低分：", scores.min())

print("\n每个学生的平均分：")
student_means = scores.mean(axis=1)  # 结果长度为 3，与学生数量一致
for i, name in enumerate(names):
    print(f"  {name}: {student_means[i]:.1f}")

print("\n每门课的平均分：")
subject_means = scores.mean(axis=0)  # 结果长度为 4，与科目数量一致
for i, subject in enumerate(subjects):
    print(f"  {subject}: {subject_means[i]:.1f}")

# 每个学生的及格科目数
passed = (scores >= 60).sum(axis=1)
print("\n每人及格科目数：", passed)

# 找出所有不及格的分数
print("不及格的分数：", scores[scores < 60])
```

完整程序的思路是“先一次性算出数组，再把姓名和结果对应输出”。`(scores >= 60)` 先生成与成绩表同形状的布尔数组，`True` 在求和时相当于 1，所以 `.sum(axis=1)` 就是每名学生的及格科目数。

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

<details>
<summary>展开查看练习参考答案</summary>

```python
import numpy as np

# 练习 1：arange 的结束值不包含，因此写 21 才能得到 20
numbers = np.arange(1, 21).reshape(4, 5)
print(numbers.shape, numbers.size, numbers.dtype)
print("第 2 行：", numbers[1])       # 人类说第 2 行，索引是 1
print("最后一列：", numbers[:, -1])

# 练习 2：使用固定种子，方便核对结果
rng = np.random.default_rng(42)
random_numbers = rng.integers(0, 101, size=50)  # 101 不包含，最大可能是 100
selected = random_numbers[random_numbers > 60]
print("大于 60 的元素：", selected)
print("数量：", selected.size)

# 练习 3：3 行 4 列，按行求和得到 3 个数，按列平均得到 4 个数
matrix = rng.integers(0, 10, size=(3, 4))
row_sums = matrix.sum(axis=1)
column_means = matrix.mean(axis=0)
print("按行求和：", row_sums, row_sums.shape)          # (3,)
print("按列平均：", column_means, column_means.shape)  # (4,)
```

</details>

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


---

## 附录：本周完整示例代码

以下代码与讲义正文搭配使用，可直接运行（原始文件名：`numpy入门.py`）。

### numpy入门

```python
# ============================================================
# 第 6 周：NumPy 入门
# 目标：学会用 NumPy 处理数组和数值计算
# ============================================================
# NumPy 是 Python 最核心的科学计算库，处理大量数字非常快
# 它最核心的东西是 ndarray（多维数组）

# ---- 0. 安装和导入 ----
# 用 Anaconda 的话，numpy 一般已经装好了
# 没有的话在终端执行：python -m pip install numpy
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
``` 

