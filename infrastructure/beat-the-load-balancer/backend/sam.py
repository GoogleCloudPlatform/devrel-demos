import time

from celery.app.control import Control

from lib.celery_task import celery_app

#
control = Control(app=celery_app)
counter = 0
# Purge pending tasks
control.purge()


def get_task_id(task):
    return task.get("request", {}).get("id") or task.get("id")


#
# Clear active, reserved, and scheduled tasks in a single loop
for queue_type in ("active", "reserved", "scheduled"):
    tasks = getattr(control.inspect(), queue_type)()
    for key in ["celery@vm-main", "celery@vm-loader", "celery@vm-loader2"]:
        if key in tasks:
            del tasks[key]
    if tasks:
        for worker, task_list in tasks.items():
            for task in task_list:
                task_id = get_task_id(task)
                control.revoke(task_id, terminate=True)
                counter += 1

print(f"Cleared a total of {counter} jobs")

i = celery_app.control.inspect()
queue_name = "celery@vm-wh01"
reserved_tasks = i.reserved()[queue_name]

while True:
    time.sleep(0.5)
    tasks_reserved = i.reserved()[queue_name]
    tasks_schedule = i.scheduled()[queue_name]
    tasks_active = i.active()[queue_name]
    print(len(tasks_active), len(tasks_schedule), len(tasks_reserved))

queue_size = 0
inspector = celery_app.control.inspect()
stats = inspector.stats()
if stats is not None:
    if queue_name in stats.keys():
        total = stats[queue_name]["total"]
        if queue_name in total.keys():
            active_tasks = total[queue_name]
            if int(total_tasks) > int(active_tasks):
                queue_size = total_tasks - active_tasks
