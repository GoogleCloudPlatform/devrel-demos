FROM alpine
ENTRYPOINT while :; do nc -lp $PORT -e sh -c 'echo -e "HTTP/1.1 200 OK\n\n👋 Hello netcat"'; done
