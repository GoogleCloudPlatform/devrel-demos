# Copyright 2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# 
FROM python:3.10

# 
WORKDIR /code

# 
COPY ./requirements.txt /code/requirements.txt
COPY ./static /code/static

# 
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

# 
COPY ./main.py /code/

# 
CMD ["uvicorn", "main:app", "--proxy-headers", "--host", "0.0.0.0", "--port", "80"]
