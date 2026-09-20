# ============================================================
# 第四章：字符串
# 目标：学会处理文字，这是编程里最常用的操作之一
# ============================================================

# ---- 1. 创建字符串 ----
s1 = "双引号"
s2 = '单引号'
s3 = """三引号
可以写多行文字"""
print(s1, s2)

# ---- 2. 转义字符 ----
# 反斜杠 \ 用来表示特殊字符
print("第一行\n第二行")   # \n 换行
print("用\t制表符分隔")    # \t 制表符（相当于 Tab 键）
print("他说：\"你好\"")    # \" 表示真正的双引号

# ---- 3. 索引和切片 ----
# 字符串里的每个字符都有位置编号（从 0 开始）
text = "Hello Python"

print(text[0])        # H    第一个字符
print(text[1])        # e    第二个字符
print(text[-1])       # n    倒数第一个（负数从右往左数）

print(text[0:5])      # Hello  取第 0 到第 4 个字符（不含第 5 个）
print(text[6:])       # Python 从第 6 个取到末尾
print(text[:5])       # Hello  从头取到第 4 个

# ---- 4. 常用方法 ----
# 方法就是"挂在数据上的函数"，用 点.方法名() 调用
word = "  Hello World  "

print(len(word))          # 长度（字符个数）
print(word.upper())       # 全转大写
print(word.lower())       # 全转小写
print(word.strip())       # 去掉两端的空格
print(word.replace("World", "Python"))   # 把 World 替换成 Python
print(word.split())       # 按空格拆成列表 ['Hello', 'World']
print("hello".find("e"))  # 找字符 e 的位置，找不到返回 -1

# ---- 5. 字符串拼接与 f-string ----
first = "张"
last = "三"
print(first + last)       # 用 + 拼接

# f-string：最方便的格式化方式，在 f 后面的大括号里放变量
name = "小明"
age = 18
print(f"我叫{name}，今年{age}岁")   # 直接嵌入变量
print(f"明年我就{age + 1}岁了")    # 大括号里还可以写计算
