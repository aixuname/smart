def find(aim):
    with open("每周项目\\test.txt", "r", encoding="utf-8") as f:
        ans = f.read()
        lines = split_mixed_text(ans)
        if aim in lines:
            print("找到该内容")
        else:
            print("未找到该内容")

def aculuate(aim):
    try:
        num = 0
        with open("每周项目\\test.txt", "r", encoding="utf-8") as f:
            ans = f.read()
            lines = split_mixed_text(ans)
        for i in lines:
            if aim == i:
                num +=1
        if num > 0:
            print(f"该内容出现的次数为：{num}")
    except FileNotFoundError:
        print(f"未找到文件")
    except Exception as e:
        print(f"发生错误: {e}")

def split_mixed_text(aim):
    with open("每周项目\\test.txt", "r", encoding="utf-8") as f:
        ans = f.read()
        lines = list(ans.split())
    
    result = []

    for char in lines:
        if (('a' <= char <= 'z') or ('A' <= char <= 'Z')):
            result.append(char)
        else:
            line = list(char)
            for i in line:
                result.append(i)
    return result

def dual(aim):
    find(aim)
    aculuate(aim)

while True:
    print("-"*50)
    print("文件查找系统,输入q退出")
    aim = input("请输入要查找的内容：")
    if aim == "q":
        break
    dual(aim)