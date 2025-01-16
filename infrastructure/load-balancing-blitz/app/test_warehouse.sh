set -x

curl localhost:8000
curl localhost:8000/crash
curl localhost:8000/crash/now
curl localhost:8000/crash/status
curl localhost:8000/health
curl localhost:8000/load
curl localhost:8000/process
curl localhost:8000/reset
curl localhost:8000/score
curl localhost:8000/update/system_address

set +x
