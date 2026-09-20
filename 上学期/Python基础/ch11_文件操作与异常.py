# ============================================================
# 第十一章：文件操作与异常处理
# 目标：读写文件，以及让程序出错时不崩溃
# ============================================================

# ---- 1. 写文件 ----
# open() 打开文件，'w' 表示写入（会覆盖原内容）
with open("test.txt", "w", encoding="utf-8") as f:
    f.write("第一行\n")
    f.write("第二行\n")

# with 语句的好处：用完自动关闭文件，不用手动 close()

# 'a' 表示追加（不覆盖，接着写）
with open("test.txt", "a", encoding="utf-8") as f:
    f.write("追加的一行\n")

# ---- 2. 读文件 ----
# 'r' 表示读取
with open("test.txt", "r", encoding="utf-8") as f:
    content = f.read()        # 一次性读全部
    print(content)

with open("test.txt", "r", encoding="utf-8") as f:
    lines = f.readlines()     # 读成列表，每行是一个元素
    print(lines)

# 逐行读（最常用，省内存）
with open("test.txt", "r", encoding="utf-8") as f:
    for line in f:
        print(line.strip())   # strip 去掉每行末尾的换行符

# 打开模式速查：
# 'r' 读  'w' 写(覆盖)  'a' 追加  'b' 二进制  '+' 读写

# ---- 3. 异常处理 ----
# 程序出错时会"抛异常"，如果不处理，程序就崩溃了
# try/except 可以"接住"错误，让程序继续跑

try:
    num = int("abc")    # 这行会出错："abc" 不能转成整数
except ValueError:
    print("转换失败：不是数字")

# 捕获多种异常
try:
    result = 10 / 0     # 除零错误
except ZeroDivisionError:
    print("不能除以零！")
except Exception as e:  # 捕获所有其他异常，e 是错误信息
    print(f"出错了：{e}")

# finally：无论是否出错都会执行
try:
    f = open("不存在.txt", "r")
except FileNotFoundError:
    print("文件不存在")
finally:
    print("这行一定会执行")

# ---- 4. 常见异常类型 ----
# ValueError       值错误（类型对但值不对）
# TypeError        类型错误（类型就不对）
# ZeroDivisionError 除零错误
# FileNotFoundError 文件不存在
# IndexError       索引超出范围
# KeyError         字典里没有这个键
