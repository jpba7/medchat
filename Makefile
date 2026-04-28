.PHONY: help up down logs ps build migrate makemigrations shell createsuperuser test lint format clean

UV ?= uv
COMPOSE ?= docker compose

help:
	@echo "MedChat — atalhos de desenvolvimento"
	@echo ""
	@echo "Stack:"
	@echo "  make up              sobe todos os serviços em background"
	@echo "  make down            desce o stack (mantém volumes)"
	@echo "  make build           rebuilda imagens"
	@echo "  make logs            stream de logs"
	@echo "  make ps              status dos containers"
	@echo ""
	@echo "Django:"
	@echo "  make migrate         aplica migrations"
	@echo "  make makemigrations  gera migrations"
	@echo "  make shell           abre Django shell no container web"
	@echo "  make createsuperuser cria superuser"
	@echo ""
	@echo "Qualidade:"
	@echo "  make test            roda pytest com settings de teste"
	@echo "  make lint            ruff check + format --check"
	@echo "  make format          ruff format + check --fix"

up:
	$(COMPOSE) up -d

down:
	$(COMPOSE) down

build:
	$(COMPOSE) build

logs:
	$(COMPOSE) logs -f --tail=100

ps:
	$(COMPOSE) ps

migrate:
	$(COMPOSE) exec web $(UV) run python manage.py migrate

makemigrations:
	$(COMPOSE) exec web $(UV) run python manage.py makemigrations

shell:
	$(COMPOSE) exec web $(UV) run python manage.py shell

createsuperuser:
	$(COMPOSE) exec web $(UV) run python manage.py createsuperuser

test:
	$(COMPOSE) exec -e DJANGO_SETTINGS_MODULE=config.settings.test web $(UV) run pytest

lint:
	$(UV) run ruff check .
	$(UV) run ruff format --check .

format:
	$(UV) run ruff format .
	$(UV) run ruff check --fix .

clean:
	$(COMPOSE) down -v
