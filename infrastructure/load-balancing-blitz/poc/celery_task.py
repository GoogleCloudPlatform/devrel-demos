import time
from celery import Celery

app = Celery("tasks", broker="redis://localhost")


@app.task
def add(x, y):
    time.sleep(0.5)
    return x + y
