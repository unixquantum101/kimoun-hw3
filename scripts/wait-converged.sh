#!/usr/bin/env bash
# Runs ON the Swarm manager. Waits until a service finished its rolling update.
# usage: wait-converged.sh <service> <replicas> [timeout-seconds]
svc="$1"; want="$2"; timeout="${3:-180}"
end=$((SECONDS + timeout))
while [ "$SECONDS" -lt "$end" ]; do
  state=$(docker service inspect --format '{{if .UpdateStatus}}{{.UpdateStatus.State}}{{else}}none{{end}}' "$svc")
  repl=$(docker service ls --filter "name=$svc" --format '{{.Replicas}}')
  echo "update=$state replicas=$repl"
  case "$state" in
    rollback_*|paused) echo "Update failed: $state"; exit 1 ;;
  esac
  if [ "$state" != "updating" ] && [ "$repl" = "$want/$want" ]; then
    exit 0
  fi
  sleep 5
done
echo "Timed out waiting for $svc"
exit 1
