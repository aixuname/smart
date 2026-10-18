# ============================================================
# 第 2 周：常用数据结构
# 目标：掌握列表、元组、字典和集合四种常用容器
# ============================================================

# ============================================================
# 第一部分：列表 List
# ============================================================

# ---- 1. 创建列表 ----
# 列表用中括号 [] 表示，可以放任意类型的数据
fruits = ["苹果", "香蕉", "橙子"]
numbers = [1, 2, 3, 4, 5]
mixed = [1, "hello", 3.14, True]   # 列表里可以混合不同类型

print(fruits)
print(numbers)

# ---- 2. 索引和切片（和字符串一样）----
print(fruits[0])        # 苹果
print(fruits[-1])       # 橙子
print(numbers[1:4])     # [2, 3, 4]

# ---- 3. 修改元素（列表可以改，字符串不行）----
fruits[0] = "梨"        # 把第 0 个改成梨
print(fruits)           # ['梨', '香蕉', '橙子']

# ---- 4. 增删改查 ----
# 增
fruits.append("葡萄")     # 在末尾添加
print(fruits)

fruits.insert(1, "西瓜")  # 在指定位置插入
print(fruits)

# 删
fruits.remove("香蕉")     # 删除指定元素（按值删除）
print(fruits)

last = fruits.pop()       # 弹出最后一个元素，并返回它
print(last, fruits)

# 查
print("梨" in fruits)     # 判断元素是否在列表里，返回 True/False
print(len(fruits))        # 列表长度

# ---- 5. 遍历列表 ----
# for 循环可以一个一个取出列表里的元素（第 2 周的循环部分会详细讲）
for fruit in fruits:
    print(f"我喜欢吃{fruit}")

# ---- 6. 排序 ----
nums = [3, 1, 4, 1, 5, 9, 2]
nums.sort()               # 原地排序（改变原列表）
print(nums)

nums2 = [3, 1, 4, 1, 5]
sorted_nums = sorted(nums2)   # 返回新列表（不改变原列表）
print(nums2, sorted_nums)

# ---- 7. 列表推导式（高级但很有用）----
# 用一行代码生成一个新列表
squares = [x * x for x in range(1, 6)]   # 1 到 5 的平方
print(squares)   # [1, 4, 9, 16, 25]

# ============================================================
# 第二部分：元组、字典、集合
# ============================================================

# ---- 1. 元组 tuple ----
# 用圆括号 () 表示，和列表很像，但"不可修改"
point = (3, 5)          # 一个坐标点
names = ("小明", "小红", "小刚")

print(point[0])         # 3，可以访问
print(names[1])         # 小红

# point[0] = 10         # 报错！元组不能修改
# 元组适合存"固定不变"的数据，比如坐标、星期几

# ---- 2. 字典 dict ----
# 用花括号 {} 表示，存"键值对"（名字 -> 数据）
# 就像一本字典：通过"词"查到"解释"
person = {
    "name": "小明",
    "age": 18,
    "city": "北京"
}

print(person["name"])    # 通过键获取值：小明
print(person["age"])     # 18

# 添加 / 修改
person["height"] = 175   # 添加新键值对
person["age"] = 19       # 修改已有键的值
print(person)

# 删除
del person["city"]       # 删除某个键
print(person)

# 常用操作
print(person.keys())     # 所有键
print(person.values())   # 所有值
print(person.items())    # 所有键值对

# 遍历字典
for key, value in person.items():
    print(f"{key} 是 {value}")

# 安全取值：用 get，键不存在时不会报错
print(person.get("name"))        # 小明
print(person.get("不存在的键", "默认值"))   # 没有就返回默认值

# ---- 3. 集合 set ----
# 用花括号 {} 或 set() 表示，特点：不重复、无序
colors = {"红", "蓝", "绿", "红"}   # 重复的"红"会自动去掉
print(colors)        # 可能显示 {'蓝', '绿', '红'}，顺序不定

number_set = {1, 2, 3, 3, 2, 1}
print(number_set)    # {1, 2, 3}，自动去重

# 集合运算
set_a = {1, 2, 3}
set_b = {2, 3, 4}
print(set_a | set_b)    # 并集 {1, 2, 3, 4}
print(set_a & set_b)    # 交集 {2, 3}
print(set_a - set_b)    # 差集 {1}（在 set_a 里但不在 set_b 里）

# 去重的实用例子
duplicate_numbers = [1, 2, 2, 3, 3, 3]
unique_numbers = list(set(duplicate_numbers))
print(unique_numbers)
