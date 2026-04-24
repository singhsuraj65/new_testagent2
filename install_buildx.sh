# Create directory
mkdir -p ~/.docker/cli-plugins

# Download latest buildx
curl -L https://github.com/docker/buildx/releases/latest/download/buildx-v0.17.0.linux-amd64 -o ~/.docker/cli-plugins/docker-buildx

# Give permission
chmod +x ~/.docker/cli-plugins/docker-buildx

# Verify
docker buildx version
