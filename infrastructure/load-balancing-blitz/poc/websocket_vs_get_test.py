#!/usr/bin/env python
import time
import requests

from websockets.sync.client import connect


def hello():
    with connect("ws://localhost:8765") as websocket:
        _start_time = time.time()
        websocket.send("Hello world!")
        message = websocket.recv()
        _time_diff = round((time.time() - _start_time) * 1000, 3)
        print(f"Web Socket Roundtrip(ms): {_time_diff}")
        return _time_diff


def call_hc():
    _start_time = time.time()
    response = requests.get("http://localhost:8009/hc")
    if response.status_code == 200:
        message = "success"
    else:
        message = "failure"

    _time_diff = round((time.time() - _start_time) * 1000, 3)
    print(f"Flask App Get Roundtrip(ms): {_time_diff}")
    return _time_diff


#  Testing Get API request vs
TestIterations = 100

avg_response_time = 0
for i in range(TestIterations):
    avg_response_time += hello()

# Average Response Time: 0.59
print(f"Average Response Time: {round(avg_response_time / TestIterations ,2) }")

avg_response_time = 0

for i in range(TestIterations):
    avg_response_time += call_hc()

# Average Response Time: 4.69
print(f"Average Response Time: {round(avg_response_time / TestIterations ,2) }")
