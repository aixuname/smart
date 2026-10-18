# 第 6 周：Pandas 基础

> 本周开始没有配套的 ch 代码文件，示例都在讲义里，请边读边敲。

[讲义目录](./README.md) · [← 上一周：第 5 周](./第05周_NumPy.md) · [下一周：第 7 周 →](./第07周_Pandas进阶与可视化.md)

## 本周目标

学完这一周，你应该能：

- 说清 `Series` 和 `DataFrame` 分别是什么。
- 用 `read_csv` 读入一份真实数据，并做初步检查（`head` / `info` / `describe`）。
- 取出任意一列、多列、若干行。
- 分得清 `loc` 和 `iloc`。
- 按条件筛选数据，按某列排序。
- 新增一列、修改一列。
- **本周产出**：读一份真实 CSV，回答 5 个问题。

---

## 一、Pandas 是什么

上周的 NumPy 处理的是**纯数字矩阵**。但真实数据长这样：

| 姓名 | 城市 | 年龄 | 成绩 |
| --- | --- | --- | --- |
| 小明 | 北京 | 18 | 92 |
| 小红 | 上海 | 19 | 85 |

有文字、有数字、有列名、还可能缺几格。这就是一张**表格**，Pandas 专门干这个。

```python
import pandas as pd
import numpy as np
```

> 惯例缩写：`pandas` 写成 `pd`，`numpy` 写成 `np`。几乎所有教程都这么写，跟着来。

两个核心数据结构：

| 结构 | 是什么 | 类比 |
| --- | --- | --- |
| `Series` | 一列带标签的数据 | 表格中的一列 |
| `DataFrame` | 多列组成的表格 | 一整张 Excel 表 |

**`DataFrame` 是本阶段的主角，`Series` 是它的一列。**

## 二、创建数据

```python
import pandas as pd

df = pd.DataFrame({
    "name": ["小明", "小红", "小刚", "小美"],
    "city": ["北京", "上海", "北京", "广州"],
    "age": [18, 19, 18, 20],
    "score": [92, 85, 77, 88]
})

print(df)
```

输出：

```
  name city  age  score
0   小明   北京   18     92
1   小红   上海   19     85
2   小刚   北京   18     77
3   小美   广州   20     88
```

注意最左边那列 `0 1 2 3` 是**索引（index）**，Pandas 自动加的。

字典转 DataFrame 是最常见的创建方式：**键是列名，值是这一列的数据**。

## 三、读 CSV（真实工作里的第一步）

```python
df = pd.read_csv("scores.csv")
```

常见参数：

```python
df = pd.read_csv(
    "scores.csv",
    encoding="utf-8",      # 中文必须写，GBK 文件写 "gbk"
    sep=",",               # 分隔符，默认就是逗号
    header=0,              # 第 0 行是表头
    nrows=100              # 只读前 100 行（数据大时先试读）
)
```

> 读取失败九成是**路径**或 **encoding** 的问题。先 `print(pd.read_csv)` 之前确认文件名拼对了、文件在当前工作目录（`import os; print(os.getcwd())`）。

## 四、先看数据：三个必用函数

拿到任何数据，**先做这三步再动手分析**：

```python
df.head()          # 看前 5 行（df.head(10) 看前 10 行）
df.info()          # 看有多少行、每列什么类型、有没有缺失
df.describe()      # 看数值列的统计摘要：数量/均值/标准差/最大最小
```

还有几个常用的：

```python
print(df.shape)        # (4, 4)   4 行 4 列
print(df.columns)      # 列名列表
print(df.dtypes)       # 每列的类型
print(len(df))         # 行数
print(df["city"].unique())    # 某列有哪些不同的值
print(df["city"].value_counts())   # 每个值出现几次
```

## 五、取数据

### 1. 取列

```python
print(df["name"])            # 取一列，返回 Series
print(df[["name", "score"]]) # 取多列，注意是两层方括号
```

> 取列用**一对方括号加列名字符串**。写成 `df.name` 也能用，但列名有空格时就废了，**统一用 `df["name"]`**。

### 2. 取行：`loc` 和 `iloc`

```python
print(df.loc[0])              # 索引标签为 0 的那一行
print(df.iloc[0])             # 第 0 行（按位置）
print(df.iloc[0:2])           # 前 2 行（位置切片，含头不含尾）
print(df.loc[0:2])            # ⚠️ loc 是标签切片，含头也含尾 → 3 行
```

两者的区别：

| | `loc` | `iloc` |
| --- | --- | --- |
| 依据 | 索引**标签**（名字） | 位置**序号**（第几个） |
| 切片是否含尾 | **含** | **不含** |

```python
# 同时指定行和列
print(df.loc[0, "name"])          # 小明
print(df.iloc[0, 0])              # 小明
print(df.loc[0:1, ["name", "score"]])
```

> 新手建议：**先用 `iloc` 按位置取，稳。** `loc` 在设置过自定义索引时更好用。

## 六、筛选：只留下想要的

```python
# 单条件
print(df[df["score"] >= 85])

# 多条件：& 表示且，| 表示或，每个条件都要加括号！
print(df[(df["score"] >= 80) & (df["age"] < 19)])

# 某列的值在列表里
print(df[df["city"].isin(["北京", "上海"])])

# 取反
print(df[~(df["city"] == "北京")])
```

这套写法和上周 NumPy 的布尔索引一脉相承，只是多了列名。

## 七、排序

```python
print(df.sort_values("score"))                    # 按成绩升序
print(df.sort_values("score", ascending=False))   # 降序
print(df.sort_values(["city", "score"]))          # 先按城市，再按成绩
print(df.sort_values("score").head(3))            # 成绩最高的 3 个
```

> `sort_values` 默认**返回新表**、不动原表（和列表的 `sort()` 不同）。想改原表加 `inplace=True`，或者直接赋值：`df = df.sort_values("score")`。

## 八、新增列与修改

```python
# 新增一列：每个分数加 5 分
df["score_plus"] = df["score"] + 5

# 新增一列：按条件打标签（np.where 相当于 if/else）
import numpy as np
df["等级"] = np.where(df["score"] >= 85, "优秀", "普通")

# 修改某一列
df["score"] = df["score"] - 1

# 修改某个格子的值
df.loc[0, "score"] = 100

print(df)
```

## 九、本周产出：读真实数据回答 5 个问题

假设数据文件 `students.csv`：

```
name,city,age,score
小明,北京,18,92
小红,上海,19,85
小刚,北京,18,77
小美,广州,20,88
小强,上海,21,65
```

```python
import pandas as pd

df = pd.read_csv("students.csv", encoding="utf-8")

# 0. 先检查数据长什么样
print(df.shape)
print(df.info())

# 1. 一共有多少个学生？
print("学生人数：", len(df))

# 2. 平均分是多少？
print("平均分：", round(df["score"].mean(), 1))

# 3. 成绩最高的是谁？
top = df.sort_values("score", ascending=False).iloc[0]
print(f"最高分：{top['name']} {top['score']} 分")

# 4. 有多少人来自北京？
print("北京学生数：", len(df[df["city"] == "北京"]))

# 5. 85 分以上的学生平均年龄是多少？
print("85 分以上平均年龄：", df[df["score"] >= 85]["age"].mean())
```

> 没有现成数据？可以自己造一个 CSV（用记事本或 Excel 存成 UTF-8 编码），也可以用 `df = pd.DataFrame({...})` 直接创建。

---

## 十、常见错误对照表

| 报错 / 现象 | 原因 | 解决 |
| --- | --- | --- |
| `KeyError: 'score'` | 列名拼错 / 前后有空格 | `print(df.columns)` 看真实列名，必要时 `df.columns = df.columns.str.strip()` |
| `FileNotFoundError` | 路径不对 | `import os; print(os.getcwd())`，确认文件在那儿 |
| `UnicodeDecodeError` | 编码不对 | 加 `encoding="utf-8"`，Windows 的 Excel 另存为可能是 `"gbk"` |
| 筛选多条件报 `TypeError` | 用了 `and` 或没加括号 | 改用 `&`，每个条件加括号 |
| 筛选完想改原表，报了 SettingWithCopyWarning | 在切片上赋值 | 用 `df.loc[条件, "列名"] = 值` |
| `df[["name"]]` 和 `df["name"]` 结果不一样 | 前者是 DataFrame，后者是 Series | 正常，取多列要用两层方括号 |
| `iloc` 切出来行数比预期少 | `iloc` 含头不含尾 | 要含尾就 `iloc[0:3]` 取前 3 行 |
| 新增列全是 NaN | 用它引用的列名拼错了 | 检查列名 |

---

## 十一、课堂练习（45 分钟）

用 `pd.DataFrame` 造一份有 6 条数据的学生表（列：姓名、城市、年龄、成绩），完成：

1. 输出前 3 行和全表的 `info()`。
2. 取出「姓名」和「成绩」两列。
3. 用 `iloc` 取出第 2 到第 4 行。
4. 筛选出成绩 ≥80 且年龄 <20 的学生。
5. 按成绩降序排序，输出前两名。

## 十二、课后作业

**作业 6.1 数据初探报告（必做）**

自己找或造一份至少 30 行的 CSV（学生成绩、电影、商品、天气都可以），提交一份 `report.md`，包含：

1. 数据的行数和列数。
2. 每一列的含义和类型（用 `df.info()` 的输出来说明）。
3. 数值列的统计摘要（`describe()`）。
4. 用筛选 + 排序回答 3 个你自己提的问题，例如「最贵的商品是什么」「平均年龄是多少」。

要求：**代码能跑通**，截图或贴出关键输出。

**作业 6.2 新增列（必做）**

在作业 6.1 的数据上新增两列：

- 一列是按 `np.where` 打的分级标签（如及格/不及格）。
- 一列是由已有列算出来的新指标（如单价 = 总价 / 数量）。

## 十三、自查清单

- [ ] 我能说清 `Series` 和 `DataFrame` 的关系。
- [ ] 我拿到数据会先跑 `head()`、`info()`、`describe()` 三件事。
- [ ] 我知道取多列要写 `df[["a", "b"]]`（两层方括号）。
- [ ] 我能说清 `loc` 和 `iloc` 的两个区别。
- [ ] 我能写出带两个条件的筛选，并且知道要加括号、用 `&`。
- [ ] 我会用 `sort_values` 排序，并知道它不修改原表。
- [ ] 我能新增一列，值是另一列算出来的。
