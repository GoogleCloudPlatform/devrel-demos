from celery_task import app
from pprint import pprint

if __name__ == "__main__":
    i = app.control.inspect()
    pprint(i.reserved())
