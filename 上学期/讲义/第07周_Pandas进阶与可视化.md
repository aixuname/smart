# 第 7 周：Pandas 进阶与可视化

> 本周开始没有配套的 ch 代码文件，示例都在讲义里。**本周产出同时是本阶段的综合项目。**

[讲义目录](./README.md) · [← 上一周：第 6 周](./第06周_Pandas基础.md) · [下一周：第 8 周 →](./第08周_AI编程工具配置.md)

## 本周目标

学完这一周，你应该能：

- 用 `groupby` 做分组统计（「每个城市平均分多少」这类问题）。
- 认出缺失值，并决定是删掉还是填充。
- 用 `merge` 把两张表按某个键拼起来。
- 用 Matplotlib 画出折线、柱状、散点、直方图，并且**中文不乱码**。
- 完成综合项目：读数据 → 清洗 → 分组统计 → 出图 → 写结论。

---

## 一、`groupby`：分组统计

真实分析里最常见的问题不是「所有人平均分多少」，而是「**每个城市的**平均分多少」。这就用 `groupby`。

```python
import pandas as pd

df = pd.DataFrame({
    "name": ["小明", "小红", "小刚", "小美", "小强"],
    "city": ["北京", "上海", "北京", "广州", "上海"],
    "score": [92, 85, 77, 88, 65]
})

print(df.groupby("city")["score"].mean())
```

输出：

```
city
上海     75.0
北京     84.5
广州     88.0
Name: score, dtype: float64
```

拆解：`groupby("city")` 先按城市把行分成几堆 → `["score"]` 选出要算的列 → `.mean()` 对每堆求平均。

### 常用聚合函数

```python
g = df.groupby("city")["score"]

print(g.mean())      # 平均
print(g.sum())       # 合计
print(g.count())     # 人数（非空个数）
print(g.max(), g.min())
print(g.size())      # 每组的行数
```

### 一次算多个指标：`agg`

```python
print(df.groupby("city")["score"].agg(["mean", "max", "min", "count"]))
```

### 多个分组列

```python
print(df.groupby(["city", "age"])["score"].mean())
```

### 分组后排序、取每组第一名

```python
# 每个城市最高分的学生
print(df.loc[df.groupby("city")["score"].idxmax()])
```

> `groupby` 的结果索引变成了分组列，想还原成普通表格用 `.reset_index()`：
> `df.groupby("city")["score"].mean().reset_index()`

## 二、缺失值处理

真实数据几乎一定有缺失（Excel 里的空单元格、CSV 里的空字段），读进 Pandas 会变成 `NaN`。

### 1. 找出缺失

```python
print(df.isna())              # 每个格子是不是缺失
print(df.isna().sum())        # 每列缺了几个（最实用）
print(df.isna().sum().sum())  # 全表缺了几个
```

### 2. 删掉

```python
df.dropna()                        # 只要有缺失就删掉这行
df.dropna(subset=["score"])        # 只在 score 缺失时删这行
df.dropna(how="all")               # 整行全空才删
```

### 3. 填充

```python
df.fillna(0)                                  # 全填 0
df["score"] = df["score"].fillna(df["score"].mean())   # 用平均分填
df["city"] = df["city"].fillna("未知")                  # 文字列填「未知」
```

### 4. 怎么选？

| 情况 | 做法 |
| --- | --- |
| 缺失很少（<5%），且这列重要 | 删掉这几行 |
| 数值列，想保住其他列的信息 | 用均值 / 中位数填 |
| 文字列缺失 | 填「未知」或删掉 |
| 这列大部分都是空的 | 直接不要这列 |

> **能不能乱填？不能。** 填充会改变数据的分布，结论会失真。填充了必须在报告里写清楚「用什么填了、填了多少条」。

## 三、`merge`：把两张表拼起来

真实场景里数据常分散在多个文件。比如：

```python
students = pd.DataFrame({
    "name": ["小明", "小红", "小刚"],
    "class_id": [1, 2, 1]
})

classes = pd.DataFrame({
    "class_id": [1, 2],
    "class_name": ["一班", "二班"]
})

result = students.merge(classes, on="class_id", how="left")
print(result)
```

输出：

```
  name  class_id class_name
0   小明         1        一班
1   小红         2        二班
2   小刚         1        一班
```

`how` 参数（和 SQL 的 join 一样）：

| 值 | 意思 |
| --- | --- |
| `"inner"`（默认） | 两边都有的才保留 |
| `"left"` | 左边全保留，右边没有的填 NaN |
| `"right"` | 右边全保留 |
| `"outer"` | 两边都保留，缺的填 NaN |

## 四、其他常用小技巧

```python
# 重命名列
df.rename(columns={"score": "成绩"}, inplace=True)

# 去掉重复行
df.drop_duplicates()

# 数值列的相关系数（看两个指标是否相关）
print(df[["age", "score"]].corr())

# 对一列每个值应用函数
df["等级"] = df["score"].apply(lambda x: "优" if x >= 90 else "良")
```

---

## 五、Matplotlib 画图

### 1. 先解决中文乱码（第一步，必做）

```python
import matplotlib.pyplot as plt

plt.rcParams["font.sans-serif"] = ["SimHei"]   # 中文字体，Windows 自带
plt.rcParams["axes.unicode_minus"] = False     # 让负号正常显示
```

不加这两行，图里的中文会变成一堆方块。

> Mac 用户把 `SimHei` 换成 `Arial Unicode MS` 或 `PingFang SC`。

### 2. 折线图：看趋势

```python
days = ["周一", "周二", "周三", "周四", "周五"]
scores = [80, 85, 78, 92, 88]

plt.figure(figsize=(8, 4))
plt.plot(days, scores, marker="o", color="steelblue", label="成绩")
plt.title("本周成绩变化")
plt.xlabel("星期")
plt.ylabel("分数")
plt.grid(alpha=0.3)
plt.legend()
plt.savefig("line.png", dpi=150, bbox_inches="tight")   # 保存
plt.show()
```

### 3. 柱状图：比大小

```python
cities = ["北京", "上海", "广州"]
avg = [84.5, 75.0, 88.0]

plt.figure(figsize=(6, 4))
plt.bar(cities, avg, color=["#4C72B0", "#DD8452", "#55A868"])
plt.title("各城市平均分")
plt.ylabel("平均分")
for i, v in enumerate(avg):
    plt.text(i, v + 0.5, f"{v}", ha="center")    # 柱子上标数值
plt.savefig("bar.png", dpi=150, bbox_inches="tight")
plt.show()
```

> 横向柱状图用 `plt.barh(...)`，类别多的时候更好看。

### 4. 散点图：看两个变量有没有关系

```python
ages = [18, 19, 18, 20, 21]
scores = [92, 85, 77, 88, 65]

plt.figure(figsize=(6, 4))
plt.scatter(ages, scores, s=80, alpha=0.7)
plt.title("年龄与成绩的关系")
plt.xlabel("年龄")
plt.ylabel("成绩")
plt.show()
```

### 5. 直方图：看分布

```python
import numpy as np
scores = np.random.randint(50, 100, 200)

plt.figure(figsize=(6, 4))
plt.hist(scores, bins=10, color="steelblue", edgecolor="white")
plt.title("成绩分布")
plt.xlabel("分数")
plt.ylabel("人数")
plt.show()
```

> 散点图看「关系」，直方图看「分布」，柱状图比「类别间的大小」，折线图看「随时间的变化」。**选错图是数据分析里最常见的低级错误。**

---

## 六、综合项目：完整数据分析

这是本阶段的**综合产出**：读数据 → 清洗 → 分组统计 → 出图 → 写结论。

```python
import pandas as pd
import matplotlib.pyplot as plt

plt.rcParams["font.sans-serif"] = ["SimHei"]
plt.rcParams["axes.unicode_minus"] = False

# ===== 第 1 步：读数据 =====
df = pd.read_csv("students.csv", encoding="utf-8")
print("原始形状：", df.shape)

# ===== 第 2 步：检查与清洗 =====
print(df.info())
print("缺失情况：\n", df.isna().sum())

df["score"] = pd.to_numeric(df["score"], errors="coerce")   # 转数字，转不了的变 NaN
df = df.dropna(subset=["score"])                            # 分数缺失的行不要
df["city"] = df["city"].fillna("未知")                      # 城市缺失填「未知」

print("清洗后形状：", df.shape)

# ===== 第 3 步：分组统计 =====
by_city = df.groupby("city")["score"].agg(["mean", "count", "max"]).round(1)
print(by_city.sort_values("mean", ascending=False))

# ===== 第 4 步：出图 =====
fig, axes = plt.subplots(1, 2, figsize=(12, 4))

by_city["mean"].sort_values().plot(kind="barh", ax=axes[0], color="steelblue")
axes[0].set_title("各城市平均分")
axes[0].set_xlabel("平均分")

axes[1].hist(df["score"], bins=10, color="#55A868", edgecolor="white")
axes[1].set_title("成绩分布")
axes[1].set_xlabel("分数")

plt.tight_layout()
plt.savefig("report.png", dpi=150, bbox_inches="tight")
plt.show()

# ===== 第 5 步：给出结论（写进报告）=====
```

**报告要写清四件事：**

1. **数据从哪来、多少条**（清洗前后各多少，删了多少、为什么）。
2. **核心发现**（比如「广州平均分最高，比最低的城市高 X 分」）。
3. **图**（至少 2 张，每张图下面一句话说明它证明了什么）。
4. **结论与局限**（数据太少？缺了几个值？结论能不能推广？）

> 第 4 点最容易被忽略，但它才是分析者和「贴图的人」的区别。

---

## 七、常见错误对照表

| 报错 / 现象 | 原因 | 解决 |
| --- | --- | --- |
| 图里中文全是方块 | 没设中文字体 | 加 `plt.rcParams["font.sans-serif"] = ["SimHei"]` |
| 负号显示成方块 | 没关 unicode_minus | 加 `plt.rcParams["axes.unicode_minus"] = False` |
| `plt.show()` 之后图是空的 | 没先 `plot` 就 show，或在 Jupyter 里重复 show | 检查绘图命令顺序 |
| 图没出现 | 在脚本里没调 `show()` / 在 Jupyter 里没装 inline 后端 | 脚本末尾加 `plt.show()` |
| 两张图叠在一起 | 没开新画布 | 每张图前加 `plt.figure()` 或 `plt.subplots()` |
| 均值计算忽略了缺失行 | `mean()` 默认跳过 NaN | 正常行为；但要说明「有多少条被跳过」 |
| `groupby` 后得到的是空表 | 分组列名拼错 / 该列全是 NaN | 检查列名，先 `dropna` |
| 报 `KeyError` 在 merge 时 | `on=` 指定的列两边名字不同 | 用 `left_on=` / `right_on=` |
| `SettingWithCopyWarning` | 在筛选出来的切片上赋值 | 改成 `df.loc[条件, "列"] = 值` |

---

## 八、课堂练习（45 分钟）

用上周作业的数据表：

1. 按某个分类列做 `groupby`，算出每组的平均分和人数，并按平均值降序输出。
2. 统计每列缺失了几个值，选一列用均值填充，并说明为什么这么填。
3. 画两张图：一张柱状图（各组的平均分），一张直方图（分数分布），都带上中文标题。

## 九、课后作业（综合项目）

**作业 7.1 数据分析报告（必做，本阶段核心产出）**

1. 找一份真实数据（CSV），至少 50 行、4 列。可以从公开数据集下载，也可以自己整理（比如班级成绩、记账记录、电影清单、跑步记录）。
2. 完成「读数据 → 检查 → 清洗 → 分组统计 → 出图」全流程。
3. 提交 `分析报告.md` + 代码文件 + 至少 2 张图，报告里包含：
   - 数据来源与规模（清洗前后行数对比）
   - 缺失值处理方案（怎么处理的、处理了几条）
   - 2～3 个核心发现，每个都配图或配数据支撑
   - 一段结论与局限说明
4. **第 8 周课上会用它做 AI 工具的实战素材，所以代码一定要能跑。**

## 十、自查清单

- [ ] 我能写出「按某列分组求平均」的完整代码。
- [ ] 我知道 `groupby(...).agg(["mean","count"])` 一次出多个指标。
- [ ] 我拿到数据会先 `isna().sum()` 看缺失情况。
- [ ] 我能说清什么时候该删、什么时候该填、填了要说明什么。
- [ ] 我会用 `merge` 按一个共同列拼两张表。
- [ ] 我画图前会先设中文字体，并且知道那两行是干什么的。
- [ ] 我能根据问题选对图：趋势用折线、比大小用柱状、看关系用散点、看分布用直方。
- [ ] 我的报告里写了数据清洗前后的行数变化。
