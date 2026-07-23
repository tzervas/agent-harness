#!/usr/bin/env bash
# Install the durable supervisor as a systemd --user unit.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEST="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"
BACKLOG="${XDG_CONFIG_HOME:-$HOME/.config}/agent-harness/backlog.json"

mkdir -p "$DEST" "$(dirname "$BACKLOG")"
install -m 0644 "$HERE/agent-harness-loop.service" "$DEST/"
install -m 0644 "$HERE/agent-harness-loop.timer" "$DEST/"

if [ ! -f "$BACKLOG" ]; then
  echo '{"units": []}' > "$BACKLOG"
  echo "seeded empty backlog: $BACKLOG"
fi

systemctl --user daemon-reload
echo "installed. enable with:"
echo "  systemctl --user enable --now agent-harness-loop.timer"
echo "an empty backlog is a no-op tick, so enabling before queueing work is safe."
