# Node parameters
NPM=npm

.PHONY: all test test-e2e build lint run clean

all: lint test build

build:
	$(NPM) run build

test:
	$(NPM) run test -- --run

test-e2e:
	$(NPM) run test:e2e

lint:
	$(NPM) run lint

run:
	$(NPM) run dev

clean:
	rm -rf dist
	rm -rf node_modules
