# CaSSAndRA (next) – all commands run from this folder.

VERSION ?= $(shell git describe --tags --always --dirty 2>/dev/null || echo dev)
LDFLAGS := -s -w -X main.version=$(VERSION)
UI_DIST := backend/server/dist
BIN     := bin/cassandra

.PHONY: help setup test test-go test-cpp test-web test-e2e coverage lint lint-go lint-web fmt build build-web dev clean

help: ## List all targets
	@grep -E '^[a-z0-9-]+:.*## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*## "}; {printf "  %-12s %s\n", $$1, $$2}'

setup: ## Install frontend dependencies and Playwright browser
	cd web && npm ci && npx playwright install chromium

test: test-go test-web ## Unit and architecture tests (backend + frontend)

test-go: ## Backend tests
	cd backend && go test -race -timeout 120s ./tests/...

test-cpp: ## Backend tests including the real C++ planner
	cd backend && go test -race -timeout 120s -tags cpp ./tests/...

test-web: ## Frontend unit and architecture tests
	cd web && npx vitest --run

test-e2e: ## End-to-end tests against the built binary
	cd web && npx playwright test

coverage: ## Backend coverage report across all features
	cd backend && go test -coverpkg=./... -coverprofile=coverage.out ./tests/... && go tool cover -func=coverage.out | tail -1

lint: lint-go lint-web ## All linters and type checks

lint-go:
	cd backend && go vet ./... && golangci-lint run ./...

lint-web:
	cd web && npm run check && npm run lint

fmt: ## Format all code
	cd backend && golangci-lint fmt ./...
	cd web && npm run format

build-web:
	cd web && npm run build
	find $(UI_DIST) -mindepth 1 ! -name .gitkeep -delete
	cp -R web/build/. $(UI_DIST)/

build: build-web ## Single binary with embedded frontend -> bin/cassandra
	cd backend && go build -ldflags "$(LDFLAGS)" -o ../$(BIN) .

dev: ## Backend on :8050 and Vite dev server with hot reload
	@trap 'kill 0' INT TERM; \
	(cd backend && go run . --host 127.0.0.1 --port 8050 --log-level debug --data-dir ../.dev-data) & \
	(cd web && npm run dev) & \
	wait

clean: ## Remove build output
	rm -rf bin web/build backend/coverage.out .e2e-data
	find $(UI_DIST) -mindepth 1 ! -name .gitkeep -delete
