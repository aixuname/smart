# ============================================================
# 第五章：列表 List
# 目标：学会用列表一次存放多个数据
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
# for 循环可以一个一个取出列表里的元素（第八章会详细讲）
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
