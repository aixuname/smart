# ============================================================
# 第三章：运算符
# 目标：学会用各种运算符做计算和判断
# ============================================================

# ---- 1. 算术运算符 ----
a = 10
b = 3

print(a + b)     # 13   加法
print(a - b)     # 7    减法
print(a * b)     # 30   乘法
print(a / b)     # 3.333...  除法（结果一定是小数）
print(a // b)    # 3    整除（只取整数部分）
print(a % b)     # 1    取余（求余数）
print(a ** b)    # 1000 幂运算（10 的 3 次方）

# ---- 2. 比较运算符（结果是 True 或 False）----
x = 5
y = 10

print(x == y)    # False  等于（注意是两个等号！）
print(x != y)    # True   不等于
print(x < y)     # True   小于
print(x > y)     # False  大于
print(x <= y)    # True   小于等于
print(x >= y)    # False  大于等于

# 注意：一个等号是赋值，两个等号才是比较
# x = 5  是"把 5 给 x"
# x == 5 是"x 等于 5 吗？"

# ---- 3. 逻辑运算符 ----
p = True
q = False

print(p and q)   # False  且：两边都为真才为真
print(p or q)    # True   或：只要一边为真就为真
print(not p)     # False  非：取反

# 常见用法：判断一个数是否在某个范围内
age = 20
print(age > 10 and age < 30)   # True，10 和 30 之间

# ---- 4. 赋值运算符 ----
n = 5
n += 3          # 相当于 n = n + 3，n 现在是 8
print(n)

n -= 2          # n = n - 2
print(n)

n *= 4          # n = n * 4
print(n)
