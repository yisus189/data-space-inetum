#!/bin/bash
# Script to initialize MinIO bucket for Data Space transfers

set -e

echo "Waiting for MinIO to be ready..."
until mc alias set local http://minio:9000 minioadmin minioadmin123; do
  echo "MinIO not ready yet, waiting..."
  sleep 2
done

echo "MinIO is ready. Creating bucket 'dataspace-transfers'..."
mc mb --ignore-existing local/dataspace-transfers

echo "Setting bucket policy to public read..."
mc anonymous set download local/dataspace-transfers

echo "MinIO bucket 'dataspace-transfers' created successfully!"
