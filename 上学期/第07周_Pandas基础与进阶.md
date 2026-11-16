# 第 7 周：Pandas 基础与进阶

> 本周是本学期内容密度最高的一周：**Pandas 的全部核心操作压缩在一节课里**。课上跟不上不要慌，按「自查清单」逐项回去补，周末专门抽一次时间做完作业。

[课程目录](../README_上学期.md) · [← 上一周：第 6 周](./第06周_NumPy.md) · [下一周：第 8 周 →](./第08周_可视化与综合项目.md)

## 本周目标

学完这一周，你应该能：

- 说清 `Series` 和 `DataFrame` 是什么，用 `read_csv` 读入真实数据。
- 拿到数据先做三件事：`head()` / `info()` / `describe()`。
- 取出任意列、行、区域，分清 `loc` 和 `iloc`。
- 按条件筛选、按某列排序、新增计算列。
- 用 `groupby` 回答「每个分组怎么样」这类问题。
- 认出缺失值，并决定删掉还是填充，**填了要说明**。
- 用 `merge` 把两张表按一个共同列拼起来。
- **本周产出**：读一份 CSV，完成「检查 → 筛选 → 分组统计」并输出一张汇总表。

> **代码阅读约定**：本周不要只背函数名。每段代码都先回答三个问题：输入表有多少行列？这一行返回新表还是修改原表？运行后行数、列数或数据类型发生了什么？

---

## 一、Pandas 是什么

第 6 周的 NumPy 处理**纯数字矩阵**。但真实数据长这样：

| 姓名 | 城市 | 年龄 | 成绩 |
| --- | --- | --- | --- |
| 小明 | 北京 | 18 | 92 |
| 小红 | 上海 | 19 | 85 |

有文字、有数字、有列名、还可能缺几格——这就是一张**表格**，Pandas 专门干这个。

```python
import pandas as pd
import numpy as np
```

> 惯例：`pandas` 写 `pd`，`numpy` 写 `np`。跟着来，别自己起名。

| 结构 | 是什么 | 类比 |
| --- | --- | --- |
| `Series` | 一列带标签的数据 | 表格中的一列 |
| `DataFrame` | 多列组成的表格 | 一整张 Excel 表 |

**`DataFrame` 是主角，`Series` 是它的一列。**

还要分清三个概念：**列名**说明每列是什么，**索引**标识每一行，**值**才是单元格中的数据。索引不一定是 `0、1、2`，也可能是学号或日期，因此后面才需要区分 `loc` 和 `iloc`。

## 二、创建与读取

```python
df = pd.DataFrame({
    "name": ["小明", "小红", "小刚", "小美"],
    "city": ["北京", "上海", "北京", "广州"],
    "age": [18, 19, 18, 20],
    "score": [92, 85, 77, 88]
})
print(df)
```

最左边 `0 1 2 3` 是**索引（index）**，Pandas 自动加的。

字典的每个键会成为列名，每个列表会成为这一列的数据，并且各列长度必须相同。可以用 `type(df)` 和 `type(df["name"])` 分别观察 `DataFrame` 与 `Series`。

真实工作里第一行代码永远是读文件：

```python
df = pd.read_csv(
    "scores.csv",
    encoding="utf-8",   # 中文必须写；GBK 文件写 "gbk"
    sep=",",            # 分隔符，默认就是逗号
    nrows=100           # 数据大时先只读前 100 行试试
)
```

> 读取失败九成是**路径**或 **encoding**。先 `import os; print(os.getcwd())` 确认文件在哪。

## 三、拿到数据先做三件事

```python
print(df.head())      # 前 5 行，确认列名和数据是否读对
df.info()             # 直接把结构信息打印到屏幕；不要再套 print
print(df.describe())  # 数值列统计：数量、均值、标准差、四分位数等
```

`df.info()` 的返回值是 `None`，因此写 `print(df.info())` 会在信息末尾多打印一个 `None`。这不是数据内容，也不是报错。

再补充几个常用的：

```python
print(df.shape)                    # (4, 4)  4 行 4 列
print(df.columns)                  # 列名
print(df["city"].unique())         # 这列有哪些不同值
print(df["city"].value_counts())   # 每个值出现几次
```

## 四、取数据

### 取列

```python
print(df["name"])              # 一列，返回 Series
print(df[["name", "score"]])   # 多列，两层方括号
```

> 统一用 `df["name"]`，别写 `df.name`——列名带空格时就废了。

### 取行：`loc` 与 `iloc`

```python
print(df.loc[0])         # 索引标签为 0 的行
print(df.iloc[0])        # 第 0 行（按位置）
print(df.iloc[0:2])      # 前 2 行（含头不含尾）
print(df.loc[0, "name"]) # 指定行列
```

| | `loc` | `iloc` |
| --- | --- | --- |
| 依据 | 索引**标签** | 位置**序号** |
| 切片含尾吗 | **含** | **不含** |

例如索引是 `[101, 103, 108]` 时，`df.loc[103]` 找标签 103，而 `df.iloc[1]` 找位置为 1 的第二行；两者碰巧可能指向同一行，但思路完全不同。

### 筛选

```python
print(df[df["score"] >= 85])                            # 单条件
print(df[(df["score"] >= 80) & (df["age"] < 19)])       # 多条件：& 且、| 或，每个条件都要括号
print(df[df["city"].isin(["北京", "上海"])])             # 在列表里
print(df[~(df["city"] == "北京")])                       # 取反
```

> 和第 6 周 NumPy 的布尔索引一模一样，只是多了列名。**`and` / `or` 在这里不能用。**

### 排序

```python
df.sort_values("score")                    # 升序
df.sort_values("score", ascending=False)   # 降序
df.sort_values(["city", "score"])          # 多列排序
df.sort_values("score", ascending=False).head(3)  # 先降序，再取成绩最高的 3 个
```

> `sort_values` **返回新表、不改原表**（和列表的 `sort()` 不同）。

## 五、新增与修改列

```python
df["score_plus"] = df["score"] + 5                                  # 由已有列算出来
df["等级"] = np.where(df["score"] >= 85, "优秀", "普通")             # 条件打标签
df["score"] = df["score"] - 1                                       # 改整列
df.loc[0, "score"] = 100                                            # 改一格
df.rename(columns={"score": "成绩"}, inplace=True)                   # 改列名
```

除非明确需要修改原表，本讲义更推荐把结果赋给新变量，例如 `renamed_df = df.rename(...)`。这样便于比较修改前后，也能减少 `inplace=True` 带来的误操作。

## 六、`groupby`：分组统计（本周重点）

真实问题几乎都是「**每个分组**怎么样」，不是「总体怎么样」。

```python
print(df.groupby("city")["score"].mean())
```

```
city
上海     75.0
北京     84.5
广州     88.0
```

三步拆解：`groupby("city")` 按城市分成几堆 → `["score"]` 选出要算的列 → `.mean()` 每堆求平均。

```python
g = df.groupby("city")["score"]
print(g.mean(), g.sum(), g.count(), g.max(), g.min())

# 一次算多个指标（最常用）
print(df.groupby("city")["score"].agg(["mean", "max", "min", "count"]))

# 多个分组列
print(df.groupby(["city", "age"])["score"].mean())

# 每个城市最高分的那一行
print(df.loc[df.groupby("city")["score"].idxmax()])

# 把分组结果变回普通表格
print(df.groupby("city")["score"].mean().reset_index())
```

以 `groupby + agg` 为例，Pandas 的执行过程不是逐行打印，而是：

1. 根据 `city` 找出每个分组包含哪些行。
2. 从各组中只取 `score` 列。
3. 对每组分别运行 `mean/max/min/count`。
4. 把每组的结果组合成一张新表。

`count` 只统计非缺失值；若想统计每组原始行数，应使用 `.size()`。有缺失值时两者可能不同。

> 数学穿插：这里算的平均值和标准差（`.std()`），就是统计学里的**均值**和**方差**。均值代表「中心在哪」，标准差代表「数据散不散」——同样一组平均分，标准差小的班级成绩更整齐。

## 七、缺失值：先看清楚，再决定怎么办

真实数据几乎一定有缺失，读进 Pandas 会变成 `NaN`。

```python
print(df.isna().sum())        # 每列缺几个（最实用的一行）
print(df.isna().sum().sum())  # 全表缺几个

df.dropna()                          # 有缺失就删这行
df.dropna(subset=["score"])          # 只在 score 缺失时删
df["score"] = df["score"].fillna(df["score"].mean())   # 用均值填
df["city"] = df["city"].fillna("未知")                  # 文字列填「未知」
```

上面的 `dropna()` 和前两个 `fillna()` 示例如果没有赋值，只是返回处理后的新表。真正要保留结果，应写成 `df = df.dropna(...)` 或 `df["score"] = ...`。处理前先记录数量，处理后再核对：

```python
missing_before = df["score"].isna().sum()       # 填充前缺多少条
fill_value = df["score"].median()               # 中位数不容易被极端值拉偏
df["score"] = df["score"].fillna(fill_value)   # 保存填充后的结果
missing_after = df["score"].isna().sum()        # 应当变成 0
print(f"score 填充 {missing_before - missing_after} 条，填充值为 {fill_value}")
```

| 情况 | 做法 |
| --- | --- |
| 缺失很少（<5%）且这列重要 | 删掉这几行 |
| 数值列，想保住其他列信息 | 用均值 / 中位数填 |
| 文字列缺失 | 填「未知」或删 |
| 这列大半是空的 | 直接不要这列 |

> **能不能乱填？不能。** 填充会改变数据分布，结论会失真。填了必须在报告里写清楚「用什么填了、填了几条、清洗前后各多少行」。

## 八、`merge`：两张表拼起来

```python
students = pd.DataFrame({"name": ["小明", "小红"], "class_id": [1, 2]})
classes  = pd.DataFrame({"class_id": [1, 2], "class_name": ["一班", "二班"]})

print(students.merge(classes, on="class_id", how="left"))
```

`on="class_id"` 指定两张表共同的连接键。连接前应检查键是否重复，否则可能出现“一行突然变成多行”：

```python
print(students["class_id"].duplicated().sum())  # 学生表中班级号可以重复
print(classes["class_id"].duplicated().sum())   # 班级表中班级号应当唯一

result = students.merge(
    classes,
    on="class_id",
    how="left",
    validate="many_to_one"  # 多名学生对应一个班级；关系不符时直接报错
)
```

| `how` | 意思 |
| --- | --- |
| `"inner"`（默认） | 两边都有的才保留 |
| `"left"` | 左边全留，右边没有的填 NaN |
| `"outer"` | 两边都留 |

---

## 九、本周产出

```python
import pandas as pd
import numpy as np

# 1. 读
df = pd.read_csv("students.csv", encoding="utf-8")

# 2. 检查
print("形状：", df.shape)
df.info()  # info 会自行输出，返回值是 None
print("缺失：\n", df.isna().sum())

# 3. 清洗
df["score"] = pd.to_numeric(df["score"], errors="coerce")   # 转数字，转不了的变 NaN
before = len(df)
df = df.dropna(subset=["score"])
df["city"] = df["city"].fillna("未知")
print(f"清洗：删除 {before - len(df)} 行，剩 {len(df)} 行")

# 4. 筛选 + 分组统计
print("\n85 分以上的同学：")
print(df[df["score"] >= 85][["name", "city", "score"]])

summary = df.groupby("city")["score"].agg(["count", "mean", "max"]).round(1)
summary = summary.sort_values("mean", ascending=False)
print("\n各城市汇总：")
print(summary)

# 5. 导出
summary.to_csv("summary.csv", encoding="utf-8-sig")
```

> `encoding="utf-8-sig"` 是给 Excel 用的——不加的话用 Excel 打开可能中文乱码。这个小细节很多人被坑过。

这段完整程序按“读取—检查—清洗—分析—导出”分层。每一步都输出可核对的信息：清洗阶段报告删除行数，分析阶段显示汇总表，导出阶段生成可交付文件。若结果不对，就能迅速定位是哪一步开始变化。

## 十、常见错误对照表

| 报错 / 现象 | 原因 | 解决 |
| --- | --- | --- |
| `KeyError: 'score'` | 列名拼错或有空格 | `print(df.columns)` 看真实列名 |
| `FileNotFoundError` | 路径不对 | `print(os.getcwd())` 确认位置 |
| `UnicodeDecodeError` | 编码不对 | 加 `encoding="utf-8"`，或换 `"gbk"` |
| 多条件筛选报 `TypeError` | 用了 `and` 或没加括号 | 用 `&`，每个条件加括号 |
| `SettingWithCopyWarning` | 在切片上赋值 | 改成 `df.loc[条件, "列"] = 值` |
| `iloc` 切出来少一行 | `iloc` 含头不含尾 | `iloc[0:3]` 才是前 3 行 |
| 新增列全是 NaN | 引用的列名拼错 | 检查列名 |
| 分组结果索引很怪 | 分组列变成了索引 | `.reset_index()` |
| `mean()` 结果比手算的高 | 它自动跳过了 NaN | 正常，但要说明跳过了几条 |
| Excel 打开导出文件中文乱码 | 没加 BOM | `to_csv(..., encoding="utf-8-sig")` |

## 十一、课堂练习（45 分钟）

1. 用 `pd.DataFrame` 造一份 6 行学生表（姓名、城市、年龄、成绩），输出前 3 行和 `info()`。
2. 取出「姓名」「成绩」两列；用 `iloc` 取第 2～4 行。
3. 筛选成绩 ≥80 且年龄 <20 的同学，按成绩降序排。
4. 按城市分组，算出每组人数、平均分、最高分，并按平均分降序输出。
5. 手工把那 6 行里的两个成绩改成空值，统计缺失并说明你选择删还是填、为什么。

<details>
<summary>展开查看课堂练习参考代码</summary>

```python
import numpy as np
import pandas as pd

# 1. 创建 6 行数据；np.nan 表示缺失值
practice = pd.DataFrame({
    "name": ["小明", "小红", "小刚", "小美", "小林", "小周"],
    "city": ["北京", "上海", "北京", "广州", "上海", "广州"],
    "age": [18, 19, 20, 18, 19, 21],
    "score": [92, 85, 77, 88, np.nan, np.nan]
})
print(practice.head(3))
practice.info()

# 2. 两层方括号返回 DataFrame；iloc 的结束位置 4 不包含
print(practice[["name", "score"]])
print(practice.iloc[1:4])  # 第 2～4 行，对应位置 1、2、3

# 3. 多条件分别加括号，并用 & 连接
selected = practice[(practice["score"] >= 80) & (practice["age"] < 20)]
print(selected.sort_values("score", ascending=False))

# 4. count 不包含缺失成绩，mean 和 max 默认跳过 NaN
summary = practice.groupby("city")["score"].agg(["count", "mean", "max"])
print(summary.sort_values("mean", ascending=False))

# 5. 此例只有 6 行，直接删除会损失三分之一数据，因此用中位数填充并记录数量
missing_count = practice["score"].isna().sum()
median_score = practice["score"].median()
practice["score"] = practice["score"].fillna(median_score)
print(f"用中位数 {median_score} 填充了 {missing_count} 条成绩")
```

</details>

## 十二、课后作业

**作业 7.1 数据初探报告（必做）**

自己找或造一份至少 30 行的 CSV（成绩、电影、商品、天气都行），提交 `report.md` 包含：

1. 行数、列数、每列的含义和类型。
2. 数值列的统计摘要。
3. 缺失值统计 + 你的处理方案（填了什么、填了几条、为什么这么选）。
4. 一次 `groupby` 分组汇总（导出成 `summary.csv`）。
5. 用筛选 + 排序回答 3 个你自己提的问题。

要求：**代码能跑通**，贴关键输出。第 8 周会用它画图，所以数据文件要留着。

**作业 7.2 合并两张表（选做）**

自己造两张有关系的小表（如「学生表 + 班级表」），用 `merge` 拼起来，分别试 `how="inner"` 和 `how="left"`，说明结果行数差在哪里、为什么。

## 十三、自查清单

- [ ] 我能说清 `Series` 和 `DataFrame` 的关系。
- [ ] 我拿到数据会先跑 `head()`、`info()`、`describe()`。
- [ ] 我知道取多列要写 `df[["a","b"]]`。
- [ ] 我能说清 `loc` 和 `iloc` 的两个区别。
- [ ] 我能写出带两个条件的筛选，并且加了括号、用了 `&`。
- [ ] 我会 `groupby + agg` 一次算出多个指标。
- [ ] 我能说清什么时候删缺失值、什么时候填、填了要交代什么。
- [ ] 我会用 `merge` 按共同列拼表。
- [ ] 我知道导出 CSV 给 Excel 用时该加 `utf-8-sig`。
