from random import randint


number = randint(1,100)
print(number)
c=int(input("请输入你要挑战的次数："))
a=1
while True :
    number_a=int(input(f"请输入第{a}次猜的数字："))
    if a<c:
        if number_a >number :
            print(f"猜大了,还剩{c-a}次机会")
            a+=1
        elif number_a< number:
            print(f"猜小了,还剩{c-a}次机会")
            a+=1
        else :
            print(f"在第{a}次就猜对了 ")
            break
    else :
        if number==number_a:
            print(f"最后一次猜对了")
            break
        else:
            print(f"猜错了,游戏结束，所猜数字为{number_a}")
            break

  
    
