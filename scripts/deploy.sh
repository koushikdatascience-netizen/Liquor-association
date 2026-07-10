#!/bin/bash
# Exit on any error
set -e

# Pull latest changes from the remote repository
echo "Pulling latest changes from origin/master..."
git pull origin master

# Build or pull Docker images if needed (optional)
# Uncomment the following line if you have a Dockerfile to build
# docker build -t liquor-association:latest .

# Restart Docker containers using docker-compose
echo "Restarting Docker containers..."
docker-compose down
docker-compose up -d --remove-orphans

echo "Deployment completed successfully."