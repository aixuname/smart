# ============================================================
# 第二章：变量与数据类型
# 目标：学会用变量存数据，认识 4 种基本类型
# ============================================================

# ---- 1. 变量 ----
# 变量就是一个"有名字的盒子"，用来存放数据
# 用等号 = 把右边的值装进左边的名字里
name = "小明"        # 把字符串装进 name
age = 18             # 把整数装进 age
height = 1.75        # 把小数装进 height

print(name, age, height)

# 变量可以随时重新赋值（改变盒子里的东西）
age = 19
print("新的年龄：", age)

# ---- 2. 四种基本类型 ----
# int      整数
# float    小数（浮点数）
# str      字符串（文字）
# bool     布尔值（只有 True 和 False 两种）

a = 10            # int 整数
b = 3.14          # float 小数
c = "hello"       # str 字符串
d = True          # bool 布尔值

# type() 可以查看一个变量的类型
print(type(a))    # <class 'int'>
print(type(b))    # <class 'float'>
print(type(c))    # <class 'str'>
print(type(d))    # <class 'bool'>

# ---- 3. 类型转换 ----
# 不同类型之间可以转换，用 int() / float() / str()
num_text = "100"        # 这是字符串，不是数字
num = int(num_text)     # 转成整数
print(num + 50)         # 150，数字可以加减

num2 = 3.9
print(int(num2))        # 3，int() 会直接去掉小数部分（不是四舍五入）

print(str(100))         # "100"，数字转成字符串
print(type(str(100)))   # <class 'str'>
