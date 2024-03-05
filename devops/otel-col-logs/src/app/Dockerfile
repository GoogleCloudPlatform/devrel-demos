# Copyright 2024 Yoshi Yamaguchi
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

FROM golang:1.21.6-bookworm as builder
WORKDIR /dist
COPY go.mod main.go ./
RUN go mod download
RUN go build -o app

FROM gcr.io/distroless/base-debian12
COPY --from=builder /dist/app /app
EXPOSE 8080
CMD ["/app"]
