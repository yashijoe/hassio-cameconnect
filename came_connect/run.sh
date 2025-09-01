#!/usr/bin/env sh
set -e

if [ -f /data/options.json ]; then
  CAME_CONNECT_CLIENT_ID=$(jq -r '.came_connect_client_id' /data/options.json)
  CAME_CONNECT_CLIENT_SECRET=$(jq -r '.came_connect_client_secret' /data/options.json)
  CAME_CONNECT_USERNAME=$(jq -r '.came_connect_username' /data/options.json)
  CAME_CONNECT_PASSWORD=$(jq -r '.came_connect_password' /data/options.json)
  export CAME_CONNECT_CLIENT_ID CAME_CONNECT_CLIENT_SECRET CAME_CONNECT_USERNAME CAME_CONNECT_PASSWORD
fi

exec uvicorn app.main:app --host 0.0.0.0 --port 8080

