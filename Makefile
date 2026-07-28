.PHONY: infra down reset logs psql redis-cli status

infra:           ## Start PostgreSQL + Redis in Docker
	docker compose up -d
	@echo "Waiting for PostgreSQL..."
	@until docker compose exec postgres pg_isready -U postgres -q 2>/dev/null; do sleep 1; done
	@echo "Ready."

down:            ## Stop infra containers
	docker compose down

reset:           ## Stop infra + delete volumes (full reset)
	docker compose down -v

logs:            ## Tail all container logs
	docker compose logs -f

psql:            ## Open psql shell
	docker compose exec postgres psql -U postgres

redis-cli:       ## Open redis-cli shell
	docker compose exec redis redis-cli

status:          ## Show container status
	docker compose ps
