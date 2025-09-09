#!/bin/bash

# This script automates the versioning and building of the Docker image.

# --- Configuration ---
IMAGE_NAME="fentanest/topheroes-applier"
VERSION_FILE="VERSION"

# --- Version Handling ---
# Check if VERSION file exists, if not, create it with a default version
if [ ! -f "$VERSION_FILE" ]; then
    echo "1.0.0" > "$VERSION_FILE"
fi

# Read the current version
CURRENT_VERSION=$(cat "$VERSION_FILE")

# Increment the patch version (e.g., 1.0.0 -> 1.0.1)
# Uses awk to split by '.' and increment the last field
NEW_VERSION=$(echo "$CURRENT_VERSION" | awk -F. -v OFS=. '{$NF = $NF + 1;} 1')

echo "Current version: $CURRENT_VERSION"
echo "New version: $NEW_VERSION"

# --- Docker Build ---
echo "Building and pushing Docker image with tags: latest, $NEW_VERSION"

docker buildx build --platform linux/amd64,linux/arm64 \
  -t "${IMAGE_NAME}:latest" \
  -t "${IMAGE_NAME}:${NEW_VERSION}" \
  --push \
  .

# Check if the build was successful
if [ $? -eq 0 ]; then
    echo "Docker image built and pushed successfully."
    # Update the version file with the new version
    echo "$NEW_VERSION" > "$VERSION_FILE"
    echo "Version updated to $NEW_VERSION"
else
    echo "Error: Docker build failed."
    exit 1
fi
