import numpy as np
# 在一个理科班有20名学生,有语文,数学,英语,物理,化学,生物6门科目,各科满分均为100分
subject=["语文","数学","英语","物理","化学","生物"]
Achievement=np.random.randint(1,101,size=(20,6))
#1.计算各科目的平均分
def Average(a):
    Average1=np.mean(a,axis=0)
    for i in range(0,6):
        print(f"{subject[i]}的平均分为{Average1[i]}")
    return
#2.求找出每一科目的最高分和最低分
def Highest_and_Lowest_score(a): 
    Lowest_score=np.min(a,axis=0)
    Highest_score=np.max(a,axis=0)
    for i in range(0,6):
        print(f"{subject[i]}的最高分为{Highest_score[i]}")
        print(f"{subject[i]}的最低分为{Lowest_score[i]}")
    return
#3.计算每人的总分
def Total_score(a):
    Total_score1=np.sum(a,axis=1)
    for i in range(0,20):
        print(f"学生{i+1}总分{Total_score1[i]}")
    return
#4.统计各科的及格人数
def Pass(a):
    arr = np.zeros(6)
    for i in range(0,6):
        for j in range(0,20):
            if a[j][i]>60:
                arr[i]+=1
    for i in range(0,6):
        print(f"{subject[i]}的及格人数为为{arr[i]}")
    return
    
while True:
    print("学生成绩管理系统")
    print("输入0为计算学生平均分")
    print("输入1为求出每一科的最高分和最低分")
    print("输入2为计算每个人的总分")
    print("输入3为统计各科的及格人数")
    print("输入4为退出系统")
    a=int(input("请输入(0-4)"))
    
    if a==0:
        Average(Achievement)
    elif a== 1:
        Highest_and_Lowest_score(Achievement)
    elif a==2:
        Total_score(Achievement)
    elif a==3:
        Pass(Achievement)
    elif a==4:
        print("退出系统")
        break