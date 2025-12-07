
print("输入q退出")
expr = ''

while expr != 'q':
    expr = input('请输入要计算的数：')
    if 'q' in expr:
        break
    tokens = []
    nums = ''
    for i in expr:
        if i in '+-*/':
            tokens.append(float(nums))
            tokens.append(i)
            nums = ''
        else:
            nums += i
    tokens.append(float(nums))

    i = 0
    while i < len(tokens):
        if tokens[i] in ['*','/']:
            num1 = tokens[i-1]
            char = tokens[i]
            num2 = tokens[i+1]
            res = num1 * num2 if char == '*' else num1 / num2
            tokens = tokens[:i-1]+[res]+tokens[i+2:]
            i = 0
        else:
            i += 1

    c = 0
    while c < len(tokens):
        if tokens[c] in ['+','-']:
            num1 = tokens[c-1]
            char = tokens[c]
            num2 = tokens[c+1]
            res = num1 + num2 if char == '+' else num1 - num2
            tokens = tokens[:c - 1] + [res] + tokens[c + 2:]
            c = 0
        else:
            c += 1
    print(tokens[0])