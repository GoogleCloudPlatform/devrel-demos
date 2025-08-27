# Copyright 2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http:#www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

FROM ollama/ollama:0.11.7

# Listen on all interfaces, port 8080
ENV OLLAMA_HOST 0.0.0.0:8000

# Store model weight files in /models
ENV OLLAMA_MODELS /models

# Reduce logging verbosity
ENV OLLAMA_DEBUG false

# Never unload model weights from the GPU
ENV OLLAMA_KEEP_ALIVE -1 

# Store the model weights in the container image
# Replace with models supported by ollama
ENV MODEL gemma3:12b
RUN ollama serve & sleep 5 && ollama pull $MODEL 

# Start Ollama
ENTRYPOINT ["ollama", "serve"]
