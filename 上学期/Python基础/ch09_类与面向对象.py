# ============================================================
# 第九章：面向对象（类）
# 目标：用"类"来组织代码，这是基础阶段的终点
# ============================================================

# ---- 1. 什么是类和对象 ----
# 类 = 模板（设计图）
# 对象 = 根据模板造出来的具体东西（实例）
# 比如："狗"是一个类，"你家那只叫旺财的狗"是一个对象

# ---- 2. 定义一个类 ----
class Dog:
    # __init__ 是构造方法，创建对象时自动调用
    # self 代表"当前这个对象"（必须有，但不传它）
    def __init__(self, name, age):
        self.name = name      # 给对象设置"属性"
        self.age = age

    # 类里的函数叫"方法"，第一个参数必须是 self
    def bark(self):
        print(f"{self.name} 在叫：汪汪！")

    def info(self):
        print(f"{self.name} 今年 {self.age} 岁")

# ---- 3. 创建对象（实例化）----
dog1 = Dog("旺财", 3)    # 自动调用 __init__
dog2 = Dog("小白", 5)

print(dog1.name)         # 访问属性：旺财
dog1.bark()              # 调用方法
dog1.info()

# ---- 4. 封装（私有属性）----
# 名字前加两个下划线 __，表示"私有"，外部不能直接访问
class BankAccount:
    def __init__(self, owner, balance):
        self.owner = owner
        self.__balance = balance      # 私有属性

    def deposit(self, amount):        # 存钱
        self.__balance += amount

    def get_balance(self):            # 通过方法安全地查看余额
        return self.__balance

account = BankAccount("小明", 100)
account.deposit(50)
print(account.get_balance())   # 150
# print(account.__balance)     # 会报错，不能直接访问私有属性

# ---- 5. 继承 ----
# 子类继承父类，自动拥有父类的属性和方法
class Animal:
    def __init__(self, name):
        self.name = name

    def eat(self):
        print(f"{self.name} 在吃东西")

class Cat(Animal):          # Cat 继承 Animal
    def meow(self):
        print(f"{self.name} 在叫：喵喵")

cat = Cat("咪咪")
cat.eat()                   # 继承来的方法
cat.meow()                  # 自己的方法

# ---- 6. 方法重写 ----
# 子类可以重新定义父类已有的方法
class Bird(Animal):
    def eat(self):          # 重写 eat 方法
        print(f"{self.name} 在啄米吃")

bird = Bird("小黄")
bird.eat()                  # 用的是重写后的版本

# ---- 7. 魔法方法 ----
# 前后都有双下划线的特殊方法，Python 会自动调用它们
class Student:
    def __init__(self, name, score):
        self.name = name
        self.score = score

    def __str__(self):       # print(对象) 时自动调用
        return f"学生：{self.name}，成绩：{self.score}"

    def __repr__(self):      # 在列表等容器里显示时自动调用
        return self.__str__()

s = Student("小明", 90)
print(s)                     # 学生：小明，成绩：90

# ---- 8. 综合小练习 ----
# 做一个简单的"学生管理"
class StudentManager:
    def __init__(self):
        self.students = []      # 用列表存所有学生

    def add(self, name, score):
        self.students.append(Student(name, score))

    def show_all(self):
        for s in self.students:
            print(s)

manager = StudentManager()
manager.add("小明", 90)
manager.add("小红", 85)
manager.add("小刚", 92)
manager.show_all()
