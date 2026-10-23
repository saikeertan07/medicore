#!/usr/bin/env bash
# MediCore AI — One-Command Deployment Script
set -e

echo "=================================================="
echo "      MediCore AI — Production Deployment        "
echo "=================================================="

# Check Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "ERROR: Docker daemon is not running. Please start Docker."
    exit 1
fi

# Ensure .env exists
if [ ! -f .env ]; then
    echo "Creating .env from .env.example..."
    cp .env.example .env
fi

# Ensure SECRET_KEY is set and meets production security requirements (>= 32 chars)
if ! grep -q '^SECRET_KEY=.\{32,\}' .env 2>/dev/null; then
    RAND_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))" 2>/dev/null || openssl rand -hex 32 2>/dev/null)
    if grep -q '^SECRET_KEY=' .env; then
        sed -i.bak "s|^SECRET_KEY=.*|SECRET_KEY=${RAND_KEY}|" .env && rm -f .env.bak
    else
        echo "SECRET_KEY=${RAND_KEY}" >> .env
    fi
    echo "Generated cryptographically secure random SECRET_KEY in .env"
fi

echo "Building and launching containers..."
docker compose down --remove-orphans || true
docker compose up --build -d

echo "Waiting for database and backend services to become healthy..."
sleep 8

# Check backend health
MAX_RETRIES=15
COUNT=0
HEALTHY=false

while [ $COUNT -lt $MAX_RETRIES ]; do
    if curl -s http://localhost:8000/api/v1/health | grep -q '"status":"healthy"'; then
        HEALTHY=true
        break
    fi
    echo "Waiting for backend health check ($COUNT/$MAX_RETRIES)..."
    sleep 3
    COUNT=$((COUNT+1))
done

if [ "$HEALTHY" = false ]; then
    echo "WARNING: Backend health check timed out. Showing recent logs:"
    docker compose logs backend --tail=30
    exit 1
fi

echo "Seeding initial database records (if required)..."
docker compose exec -T backend python -c "
from app.core.database import SessionLocal
from app.models.models import User
db = SessionLocal()
count = db.query(User).count()
db.close()
if count == 0:
    import subprocess
    subprocess.run(['python', '-m', 'seed.seed_data'], check=True)
else:
    print(f'Database already contains {count} users. Seeding skipped.')
"

echo "=================================================="
echo "       MediCore AI Deployment Successful!        "
echo "=================================================="
echo " • Frontend UI:        http://localhost:3000"
echo " • Backend API:       http://localhost:8000"
echo " • Interactive Docs:  http://localhost:8000/docs"
echo " • Health Check:      http://localhost:8000/api/v1/health"
echo "--------------------------------------------------"
echo " Demo Logins:"
echo "   - Admin:   admin@medicore.ai   / Admin@123"
echo "   - Doctor:  doctor.chen@medicore.ai / Doctor@123"
echo "   - Patient: patient.sarah@medicore.ai / Patient@123"
echo "=================================================="
