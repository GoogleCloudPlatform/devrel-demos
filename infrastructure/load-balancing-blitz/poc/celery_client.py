import time

from celery_task import add


response_time = []

for i in range(500):
    start = time.time()
    t = add.delay(i, 12)
    diff = time.time() - start
    print(f"time difference {diff}")
    response_time.append(diff)

print(f"min { min(response_time)}")
print(f"max { max(response_time)}")
print(f"avg {sum(response_time) / len(response_time)}")
# from celery_task import add
#
# # Send a task to add 4 and 5
# result = add.delay(4, 5)

# Wait for the task to complete and get the result
# print(result.get())  # This should print 9
