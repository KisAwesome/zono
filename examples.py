import zono.Queue

q = zono.Queue.Queue(5)
for i in range(7):
    q.append(i)
print(q)