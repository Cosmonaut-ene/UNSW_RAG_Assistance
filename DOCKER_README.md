# Docker Setup for UNSW CSE Chatbot

This guide explains how to run the UNSW CSE Chatbot application using Docker.

## Prerequisites

- Docker Engine 20.10+
- Docker Compose 2.0+
- At least 2GB of available memory
- Google API key for Gemini
- Docker daemon running and user permissions configured

## Quick Start

### 1. Clone and Setup Environment

```bash
# Clone the repository
git clone <repository-url>
cd capstone-project-25t2-9900-f10a-almond

# Copy environment template to project root
cp .env.docker .env

# Your .env file is ready with the current API key
# Edit .env if you want to change any values
nano .env
```

### 2. Configure Environment Variables

Edit `.env` file with your actual credentials:

```env
# Required: Google API Key
GOOGLE_API_KEY=your-actual-google-api-key

# Optional: Change admin credentials
ADMIN_EMAIL=your-admin@unsw.edu.au
ADMIN_PASSWORD=your-secure-password

# Optional: Change secret key for production
SECRET_KEY=your-very-secure-secret-key
```

### 3. Start the Application

```bash
# Start production environment
docker-compose up -d

# Or start with logs visible
docker-compose up
```

### 4. Access the Application

- **Frontend**: http://localhost:8080 (Port 8080)
- **Backend API**: http://localhost:5000
- **Admin Panel**: http://localhost:8080/admin

## Development Setup

For development with hot-reloading:

```bash
# Start development environment
docker-compose -f docker-compose.dev.yml up

# Frontend will be available at http://localhost:3000
# Backend will be available at http://localhost:5000
```

## Commands

### Basic Operations

```bash
# Start services
docker-compose up -d

# Stop services
docker-compose down

# View logs
docker-compose logs -f

# View logs for specific service
docker-compose logs -f backend
docker-compose logs -f frontend

# Restart services
docker-compose restart

# Rebuild containers
docker-compose up --build
```

### Maintenance

```bash
# Check service status
docker-compose ps

# Execute commands in running container
docker-compose exec backend python -c "print('Backend is running')"
docker-compose exec frontend sh

# Clean up (remove containers, networks, volumes)
docker-compose down -v
docker system prune -a
```

## File Structure

```
├── docker-compose.yml          # Production configuration
├── docker-compose.dev.yml      # Development configuration
├── .env.docker                 # Environment template
├── backend/
│   ├── Dockerfile              # Backend container
│   └── .dockerignore
├── frontend/
│   ├── Dockerfile              # Frontend production container
│   ├── Dockerfile.dev          # Frontend development container
│   ├── nginx.conf              # Nginx configuration
│   └── .dockerignore
└── DOCKER_README.md            # This file
```

## Configuration Details

### Backend Container
- **Base Image**: Python 3.12 slim
- **Port**: 5000
- **Health Check**: `/api/admin/health`
- **Volumes**: Logs, docs, vector store

### Frontend Container
- **Base Image**: Node 18 Alpine (build) + Nginx Alpine (serve)
- **Port**: 80
- **Features**: Gzip compression, API proxy, static asset caching

### Network
- **Network**: `chatbot-network` (bridge)
- **Communication**: Frontend → Backend via service names

## Troubleshooting

### Common Issues

1. **Docker permission denied**
   ```bash
   # Add your user to docker group (requires logout/login)
   sudo usermod -aG docker $USER
   
   # OR run with sudo (not recommended for security)
   sudo docker-compose up
   
   # OR use Docker Desktop if on Windows/Mac
   ```

2. **Environment variable not set**
   ```bash
   # Make sure .env file exists in project root
   ls -la .env
   
   # Copy template if missing
   cp .env.docker .env
   
   # Verify environment variables are loaded
   docker-compose config
   ```

3. **Port conflicts**
   ```bash
   # Check what's using port 8080/5000
   lsof -i :8080
   lsof -i :5000
   
   # Change ports in docker-compose.yml if needed
   ports:
     - "3000:80"  # Use port 3000 instead of 8080
   ```

2. **Google API key issues**
   ```bash
   # Check environment variables
   docker-compose exec backend env | grep GOOGLE
   
   # Verify key.json file exists
   docker-compose exec backend ls -la rag/key.json
   ```

3. **Memory issues**
   ```bash
   # Check Docker memory usage
   docker stats
   
   # Increase Docker memory limit in Docker Desktop
   ```

4. **Build failures**
   ```bash
   # Clean rebuild
   docker-compose down
   docker-compose build --no-cache
   docker-compose up
   ```

### Log Analysis

```bash
# Backend logs
docker-compose logs backend | grep ERROR

# Frontend logs
docker-compose logs frontend | grep error

# All logs with timestamps
docker-compose logs -t
```

## Production Deployment

### Security Considerations

1. **Environment Variables**
   - Use strong SECRET_KEY
   - Change default admin credentials
   - Never commit .env files

2. **Network Security**
   - Use reverse proxy (nginx/traefik)
   - Enable HTTPS
   - Configure firewall rules

3. **Resource Limits**
   ```yaml
   # Add to docker-compose.yml
   services:
     backend:
       deploy:
         resources:
           limits:
             cpus: '1.0'
             memory: 512M
   ```

### Health Monitoring

```bash
# Check service health
docker-compose ps
docker inspect chatbot-backend | grep Health
docker inspect chatbot-frontend | grep Health
```

## Backup and Restore

### Backup Data

```bash
# Backup logs and vector store
docker-compose exec backend tar -czf /tmp/backup.tar.gz logs/ rag/vector_store/
docker cp chatbot-backend:/tmp/backup.tar.gz ./backup-$(date +%Y%m%d).tar.gz
```

### Restore Data

```bash
# Restore from backup
docker cp ./backup-20240101.tar.gz chatbot-backend:/tmp/
docker-compose exec backend tar -xzf /tmp/backup-20240101.tar.gz -C /app/
```

## Development Tips

1. **Live Reloading**: Use `docker-compose.dev.yml` for development
2. **Debugging**: Add `-e FLASK_DEBUG=True` for detailed error messages
3. **Database**: Logs are stored in JSONL format in `backend/logs/`
4. **API Testing**: Backend API is available at `http://localhost:5000/api`

## Support

For issues related to:
- Docker setup: Check this README and Docker logs
- Application bugs: Check application logs
- API issues: Test endpoints with curl or Postman

```bash
# Test API health
curl http://localhost:5000/api/admin/health

# Test frontend
curl http://localhost:8080/
```