.PHONY: help up down restart-bot restart-api restart logs

help:
	@echo "Available commands:"
	@echo "  make                 - Show this list of commands"
	@echo "  make up              - Start all containers"
	@echo "  make down            - Stop all containers"
	@echo "  make restart-bot     - Restart the bot container"
	@echo "  make restart-api     - Restart the REST API container"
	@echo "  make restart     - Restart all containers"
	@echo "  make logs     - Show and follow logs (last 100 lines)"

up:
	docker-compose up --build -d

down:
	docker-compose down

rebuild:
	docker-compose down
	docker-compose up --build -d

restart-bot:
	docker-compose restart bot

restart-api:
	docker-compose restart rest-api

logs:
	docker-compose logs -f --tail 100

restart:
	docker-compose restart
	docker compose logs -f --tail 100