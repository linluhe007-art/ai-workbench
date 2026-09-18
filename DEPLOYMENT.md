# AI Workbench - Production Deployment Guide

## Prerequisites

- Docker 24+ & Docker Compose v2
- 4 GB RAM minimum (8 GB recommended)
- PostgreSQL 16, Redis 7 (managed via Docker)
- Your own `scripts/nginx.prod.conf`. The production compose file mounts it as the
  reverse-proxy config, but it is **not shipped with this repository** — supply one
  before starting the stack, or remove the `nginx` service if you terminate TLS
  elsewhere.

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DB_PASSWORD` | `changeme` | PostgreSQL password |
| `DATABASE_URL` | (auto) | Full PostgreSQL connection string |
| `REDIS_URL` | `redis://redis:6379/0` | Redis connection string |
| `REDIS_ENABLED` | `true` | Enable Redis distributed runtime |
| `PERSISTENCE_ENABLED` | `true` | Enable PostgreSQL persistence |
| `RUNTIME_INSTANCE_ID` | `backend-1` | Unique instance identifier |
| `LOG_LEVEL` | `info` | Logging level |

## Quick Start

```bash
# Clone and start
git clone https://github.com/linluhe007-art/ai-workbench.git && cd ai-workbench
cp .env.example .env
docker compose -f docker-compose.prod.yml up -d

# Verify
curl http://localhost/api/v1/system/health
curl http://localhost/api/v1/system/cluster
```

## Database Migration

Migrations run automatically on first start via Alembic:

```bash
# Manual migration (if needed)
docker compose -f docker-compose.prod.yml exec backend alembic upgrade head
```

## Scaling

```bash
# Scale backend instances
docker compose -f docker-compose.prod.yml up -d --scale backend=4

# Verify cluster
curl http://localhost/api/v1/system/cluster
```

## Health Checks

| Endpoint | Purpose |
|----------|---------|
| `GET /api/v1/system/health` | Liveness probe |
| `GET /api/v1/system/readiness` | Readiness probe (DB + Redis status) |
| `GET /api/v1/system/cluster` | Cluster topology & leader |
| `GET /api/v1/system/info` | Detailed instance info |

## Graceful Shutdown

```bash
# Graceful shutdown via API
curl -X POST http://localhost/api/v1/system/shutdown

# Or SIGTERM
docker compose -f docker-compose.prod.yml stop backend
```

Shutdown sequence: Drain → Wait for tasks → Save state → Release locks → Close connections → Stop

## Leader Election

- Single instance: self-appointed leader
- Multi-instance (Redis): Redis SET NX lock with 15s TTL
- Leader refresh: automatic at half TTL (7.5s)
- Failover: max 15s lock expiry → new election

## Monitoring

- Metrics: `GET /api/v1/metrics`
- Experience stats: `GET /api/v1/experience/stats`
- Audit log: `GET /api/v1/audit`

## Troubleshooting

```bash
# Check logs
docker compose -f docker-compose.prod.yml logs backend

# Check instance status
curl http://localhost/api/v1/system/readiness

# Redis connectivity
docker compose -f docker-compose.prod.yml exec redis redis-cli ping
```