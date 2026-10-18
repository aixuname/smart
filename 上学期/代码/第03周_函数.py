# ============================================================
# 第 3 周：函数
# 目标：把一段代码打包起来，重复使用
# ============================================================

# ---- 1. 定义和调用函数 ----
# def 用来定义函数，后面是函数名和括号
def say_hello():
    print("你好！")

say_hello()     # 调用函数
say_hello()     # 可以多次调用

# ---- 2. 参数 ----
# 参数是函数需要"接收"的数据
def greet(name):
    print(f"你好，{name}")

greet("小明")
greet("小红")

# 多个参数
def add(a, b):
    return a + b      # return 把结果"返回"给调用者

result = add(3, 5)
print(result)         # 8

# ---- 3. 返回值 ----
# 函数可以 return 一个值，也可以不 return（返回 None）
def square(x):
    return x * x

print(square(4))      # 16

# ---- 4. 默认参数 ----
# 给参数一个默认值，调用时可以不传
def greet2(name, greeting="你好"):
    print(f"{greeting}，{name}")

greet2("小明")                    # 用默认的"你好"
greet2("小明", greeting="早上好")  # 覆盖默认值

# ---- 5. 关键字参数 ----
# 调用时用"参数名=值"，顺序可以乱
def info(name, age, city):
    print(f"{name} {age} 岁，来自 {city}")

info(age=20, city="上海", name="小明")

# ---- 6. 作用域 ----
# 函数内部的变量（局部变量）和外面的变量（全局变量）是分开的
x = 10            # 全局变量
def test():
    x = 5         # 这是函数内部的 x，和外面的不是同一个
    print("函数内：", x)

test()
print("函数外：", x)   # 还是 10

# ---- 7. lambda 匿名函数（进阶，可选）----
# 一行写完的简单函数
double = lambda n: n * 2
print(double(6))    # 12
