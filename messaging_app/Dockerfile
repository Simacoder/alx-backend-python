#!/bin/bash

# Docker Setup and Build Commands for Messaging App

echo "=== Docker Setup for Django Messaging App ==="

# 1. Install Docker on Linux (Ubuntu/Debian)
echo "Step 1: Installing Docker..."
sudo apt-get update
sudo apt-get install -y \
    ca-certificates \
    curl \
    gnupg \
    lsb-release

# Add Docker's official GPG key
sudo mkdir -m 0755 -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

# Add Docker repository
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker Engine
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Add user to docker group (optional, requires logout/login)
sudo usermod -aG docker $USER

echo "Docker installation completed!"

# 2. Generate requirements.txt (if you have an existing virtual environment)
echo "Step 2: Generating requirements.txt..."
# Uncomment the next line if you have an active virtual environment
# pip freeze > requirements.txt

# 3. Build Docker image
echo "Step 3: Building Docker image..."
cd messaging_app  # Navigate to your project directory
docker build -t messaging-app:latest .

# 4. Run the container (note the -p flag for port mapping)
echo "Step 4: Running the container..."
docker run -d -p 8000:8000 --name messaging-app-container messaging-app:latest

# 5. Check if container is running
echo "Step 5: Checking container status..."
docker ps

# 6. View logs
echo "Step 6: Viewing container logs..."
docker logs messaging-app-container

echo "=== Docker setup complete! ==="
echo "Your app should be accessible at http://localhost:8000"

# Additional useful commands:
echo ""
echo "=== Useful Docker Commands ==="
echo "Stop container: docker stop messaging-app-container"
echo "Start container: docker start messaging-app-container"
echo "Remove container: docker rm messaging-app-container"
echo "Remove image: docker rmi messaging-app:latest"
echo "View running containers: docker ps"
echo "View all containers: docker ps -a"
echo "Enter container shell: docker exec -it messaging-app-container /bin/bash"

