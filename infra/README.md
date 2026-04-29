# Infraestructura

## Responsable: Escobar

## Estructura
- `docker-compose.yml` — orquestación de servicios de cluster.
- `mongo/` — datos y soporte para MongoDB Replica Set.
- `postgres/` — datos y scripts de inicialización para PostgreSQL primary/standby.

## Implementación
- Configurado MongoDB Replica Set `rs0` con 3 nodos: primary + 2 secondaries.
- Configurado PostgreSQL en streaming replication con primary y standby.
- `infra/docker-compose.yml` define los servicios y las redes necesarias.

## Uso
1. Iniciar los clusters:
   ```bash
   cd infra
   docker compose up -d mongo-rrv-primary mongo-rrv-secondary-1 mongo-rrv-secondary-2 postgres-oficial-primary postgres-oficial-standby
   ```
2. Verificar el Replica Set MongoDB:
   ```bash
   docker compose exec mongo-rrv-primary mongo --eval 'rs.status()'
   ```
3. Verificar PostgreSQL primaria:
   ```bash
   docker compose exec postgres-oficial-primary pg_isready
   ```

## Notas
- El cluster MongoDB usa `mongo-rrv-primary:27017` como punto de entrada y replica al resto de miembros.
- El cluster PostgreSQL usa `postgres-oficial-primary:5432` como primary y `postgres-oficial-standby` se configura como standby de réplica.
- La aplicación backend debe usar las direcciones de servicio Docker Compose para conectarse a los clusters.
