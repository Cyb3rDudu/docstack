# Deployment Guide

## Prerequisites
- Container 111 (librechat) running
- PostgreSQL 17 on container 107
- OpenSearch 2.19.4 on container 110
- Hayhooks 1.8.0 on container 112

## Step 1: Database Setup

```sql
-- On PostgreSQL (container 107)
CREATE DATABASE docstack;
CREATE USER docstack_user WITH PASSWORD 'your_password_here';
GRANT ALL PRIVILEGES ON DATABASE docstack TO docstack_user;
```

## Step 2: Backend Deployment

```bash
# SSH to container 111
ssh root@10.36.0.111

# Create directory
mkdir -p /opt/docstack/backend
cd /opt/docstack/backend

# Clone or copy repository
# (instructions depend on how you're transferring the code)

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp .env.example .env
# Edit .env with actual credentials

# Run database migrations
alembic upgrade head

# Create systemd service (see PLAN.md for service file)
systemctl enable docstack-backend
systemctl start docstack-backend
```

## Step 3: Frontend Deployment

```bash
# Still on container 111
cd /opt/docstack/frontend

# Install dependencies
npm install

# Copy environment file
cp .env.local.example .env.local

# Build production
npm run build

# Create systemd service
systemctl enable docstack-frontend
systemctl start docstack-frontend
```

## Step 4: Nginx Configuration

See PLAN.md for nginx reverse proxy configuration.
