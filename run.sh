#!/usr/bin/env bash
# Chelsea Season Tracker 2026-27
#   ./run.sh           build from cached data/raw, run smoke test, (re)start server on :4271 with nohup
#   ./run.sh --fetch   re-fetch ESPN data first
#   ./run.sh stop      stop the server
set -euo pipefail
cd "$(dirname "$0")"
PORT=4271; PID=data/server.pid
stop(){ if [ -f "$PID" ] && kill -0 "$(cat "$PID")" 2>/dev/null; then kill "$(cat "$PID")"; sleep 0.3; fi; rm -f "$PID"; }
if [ "${1:-}" = "stop" ]; then stop; echo stopped; exit 0; fi
if [ "${1:-}" = "--fetch" ]; then python3 fetch.py; python3 fetch_logos.py; fi
python3 build.py
python3 export_snapshot.py
stop
nohup python3 server.py >> data/server.log 2>&1 &
echo $! > "$PID"; sleep 0.8
curl -sf "http://127.0.0.1:$PORT/healthz" >/dev/null && echo "serving http://127.0.0.1:$PORT/ (pid $(cat $PID))"
python3 tests/smoke_test.py || echo "SMOKE TEST FAILED"
