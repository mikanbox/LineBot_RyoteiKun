import pulp

location = ['a','b','c','d','e']#拠点名
time = 2
e = {} # 空の辞書#各拠点間時間
c = {} # 空の辞書cost   #拠点のコスト
for i in location:
    for j in location:
        e[i,j] = 1
        c[i,j] = 1



#最適化問題を解く
problem = pulp.LpProblem('sample', pulp.LpMaximize)
# xi 拠点に行くなら1
# 0-1変数を宣言
# 変数集合を表す辞書
x = {} # 空の辞書
for i in location:
    for j in location:
        x[i,j] = pulp.LpVariable("x({:},{:})".format(i,j), 0, 1, pulp.LpInteger)
y = {} # 空の辞書
for i in location:
    y[i] = pulp.LpVariable("y({:})".format(i), 0, 1, pulp.LpInteger)

problem += pulp.lpSum(c[i,j] * x[i,j] for i in location for j in location), "TotalCost"
problem += sum(x[i,j] for i in location for j in location) <= time, "Constraint_leq"
for i in location:
    for j in location:
        if i==j:
            problem += x[i,j]*2 <= 1, "Constraint_leq_{:}_{:}".format(i,j)
        continue;
        problem += sum(x[i,j]+x[j,i]) <= 1, "Constraint_leq_{:}_{:}".format(i,j)

for i in location:
    problem += sum(x[i,j] for j in location) <= 2, "Constraint_node_{:}".format(i)
for i in location:
    problem += sum(x[i,j] for j in location) <= y[i], "Constraint_node_y_{:}".format(i)


problem += sum(y[i] for i in location) - sum(x[i,j] for i in location for j in location) == 1, "Constraint_eq2"


status = problem.solve()
print ("Status", pulp.LpStatus[status])
print (problem)
print ("Result")


for i in location:
    for j in location:
        print (x[i,j], x[i,j].value())

for i in location:
    print (y[i], y[i].value())

