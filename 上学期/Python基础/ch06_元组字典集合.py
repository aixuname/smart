# ============================================================
# 第六章：元组、字典、集合
# 目标：认识另外三种常用的"容器"
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

numbers = {1, 2, 3, 3, 2, 1}
print(numbers)       # {1, 2, 3}，自动去重

# 集合运算
a = {1, 2, 3}
b = {2, 3, 4}
print(a | b)    # 并集 {1, 2, 3, 4}
print(a & b)    # 交集 {2, 3}
print(a - b)    # 差集 {1}（在 a 里但不在 b 里）

# 去重的实用例子
nums = [1, 2, 2, 3, 3, 3]
unique = list(set(nums))    # 转成集合去重，再转回列表
print(unique)
