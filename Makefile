.PHONY: up down logs test build

up:
	docker compose up -d --build

down:
	docker compose down -v

logs:
	docker compose logs -f api

build:
	docker compose build api

test:
	pytest -q
