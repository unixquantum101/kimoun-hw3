#!/usr/bin/env bash
# Run on YOUR LAPTOP during a deploy or rollback to prove the service never goes down.
# usage: ./uptime-check.sh http://<manager-public-ip>:8080     (Ctrl-C to stop)
URL="${1:?usage: uptime-check.sh http://<ip>:8080}"
while true; do
  code=$(curl -s -o /tmp/health.json -w '%{http_code}' --max-time 2 "$URL/health")
  echo "$(date +%T)  HTTP $code  $(cat /tmp/health.json 2>/dev/null)"
  sleep 0.5
done
