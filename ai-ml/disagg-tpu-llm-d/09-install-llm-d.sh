#!/bin/bash

. ./env.sh

set -x

git clone https://github.com/llm-d/llm-d.git
sudo rm -rf /usr/local/bin/yq
cd llm-d
./guides/prereq/client-setup/install-deps.sh

set +x
