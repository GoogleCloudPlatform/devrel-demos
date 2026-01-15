.PHONY: setup deploy test-local

setup:
	chmod +x deploy/setup_cloud.sh
	./deploy/setup_cloud.sh

deploy:
	chmod +x deploy/deploy.sh
	./deploy/deploy.sh

test-local:
	go test -v ./internal/...