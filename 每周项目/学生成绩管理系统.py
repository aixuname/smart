
students = []  # 格式：[{'name': '张三', 'math': 90, 'english': 85, 'chinese': 95}, ...]

def show_menu():
    print("\n学生成绩管理系统")
    print("1. 新增学生成绩")
    print("2. 查看所有学生成绩")
    print("3. 查找单个学生成绩")
    print("0. 退出系统")

def add_student():
    name = input("请输入学生姓名：")
    for stu in students:
        if stu['name'] == name:
            print(f"错误：学生{name}已存在，无需重复添加！")
            return

    math = float(input("请输入数学成绩："))
    english = float(input("请输入英语成绩："))
    chinese = float(input("请输入语文成绩："))

    student = {
        'name': name,
        'math': math,
        'english': english,
        'chinese': chinese
    }
    students.append(student)
    print(f"成功添加学生{name}的成绩！")

def show_all_students():
    if not students:
        print("暂无学生成绩记录！")
        return

    print("\n 所有学生成绩：")
    print(f"{'姓名':<8}{'数学':<8}{'英语':<8}{'语文':<8}{'总分':<8}")
    print("-" * 40)

    for stu in students:
        total = stu['math'] + stu['english'] + stu['chinese']
        print(f"{stu['name']:<8}{stu['math']:<8.1f}{stu['english']:<8.1f}{stu['chinese']:<8.1f}{total:<8.1f}")

def search_student():
    name = input("请输入要查找的学生姓名：")
    for stu in students:
        if stu['name'] == name:
            print(f"\n {name}的成绩详情：")
            print(f"数学：{stu['math']:.1f}分")
            print(f"英语：{stu['english']:.1f}分")
            print(f"语文：{stu['chinese']:.1f}分")
            print(f"总分：{stu['math']+stu['english']+stu['chinese']:.1f}分")
            return
    print(f"未找到学生{name}的成绩记录！")

while True:
    show_menu()
    choice = input("请输入功能编号（0-3）：")
    if choice == '0':
        print("退出系统，再见！")
        break
    elif choice == '1':
        add_student()
    elif choice == '2':
        show_all_students()
    elif choice == '3':
        search_student()
    else:
        print("输入错误，请输入0-3之间的编号！")