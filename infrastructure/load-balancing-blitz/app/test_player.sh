
# TODO(Developer): update location like asia-south1-c
# TODO(Developer): Update following as required # <<--------------<<--------------<<--------------
export LOCATION="us-west4-a"
# TODO(Developer): update GCLB IP address
# TODO(Developer): Update following as required # <<--------------<<--------------<<--------------
export GCLB_IP="10.2.0.2"

set -x

curl localhost:8000/
curl localhost:8000/game/start
curl localhost:8000/game/stop
curl localhost:8000/hc
curl localhost:8000/health
curl localhost:8000/load
curl localhost:8000/process
curl localhost:8000/process/options
curl localhost:8000/reset
curl localhost:8000/rr/process
curl localhost:8000/update/system_address
curl localhost:8000/vm/active

curl localhost:8000/vm/reset/vm-wh01
curl localhost:8000/vm/reset/vm-wh02
curl localhost:8000/vm/reset/vm-wh03
curl localhost:8000/vm/reset/vm-wh04

curl localhost:8000/vm/all
curl localhost:8000/vm/all/load
curl localhost:8000/vm/all/score
curl localhost:8000/vm/all/stats

curl localhost:8000/vm/select/vm-wh01
curl localhost:8000/vm/select/vm-wh02
curl localhost:8000/vm/select/vm-wh03
curl localhost:8000/vm/select/vm-wh04

curl vm-wh01.${LOCATION}.c.beat-the-load-balancer.internal:8000/process
curl vm-wh02.${LOCATION}.c.beat-the-load-balancer.internal:8000/process
curl vm-wh03.${LOCATION}.c.beat-the-load-balancer.internal:8000/process
curl vm-wh04.${LOCATION}.c.beat-the-load-balancer.internal:8000/process

curl vm-main.${LOCATION}.c.beat-the-load-balancer.internal:8000/reset

curl vm-wh01.${LOCATION}.c.beat-the-load-balancer.internal:8000/reset
curl vm-wh02.${LOCATION}.c.beat-the-load-balancer.internal:8000/reset
curl vm-wh03.${LOCATION}.c.beat-the-load-balancer.internal:8000/reset
curl vm-wh04.${LOCATION}.c.beat-the-load-balancer.internal:8000/reset

curl vm-wh91.${LOCATION}.c.beat-the-load-balancer.internal:8000/reset
curl vm-wh92.${LOCATION}.c.beat-the-load-balancer.internal:8000/reset
curl vm-wh93.${LOCATION}.c.beat-the-load-balancer.internal:8000/reset
curl vm-wh94.${LOCATION}.c.beat-the-load-balancer.internal:8000/reset

curl ${GCLB_IP}:8000/load
curl ${GCLB_IP}:8000/load
curl ${GCLB_IP}:8000/load
curl ${GCLB_IP}:8000/load
curl ${GCLB_IP}:8000/load
curl ${GCLB_IP}:8000/load
curl ${GCLB_IP}:8000/load
curl ${GCLB_IP}:8000/load


set +x
