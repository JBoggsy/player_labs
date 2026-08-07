# Stencil campaign order controller

The campaign controller runs as the per-user macOS LaunchAgent
`com.softmax.paintbot-stencil-campaign-controller`. This is the native macOS
supervisor for a process that should start at login and be restarted after a
crash. It does not require a cloud credential or store a Softmax token in its
property list; the controller reads the existing user login from
`~/.softmax/credentials.yaml`.

The service uses:

- controller: `paintbot_lab/tools/campaign_order_controller.py`
- manager: `paintbot_lab/tools/manage_campaign_order_launch_agent.py`
- property list:
  `~/Library/LaunchAgents/com.softmax.paintbot-stencil-campaign-controller.plist`
- durable state and logs:
  `~/Library/Application Support/Stencil Campaign Controller/`

The generated property list uses the checkout's absolute `.venv/bin/python`,
sets `KeepAlive`, throttles rapid relaunches to 30 seconds, and redirects stdout
and stderr to durable files. The controller holds a non-blocking file lock,
checkpoints state with atomic replace plus `fsync`, and retries campaign prompt
readback because the composed full prompt can lag a successful write. Repeated
API or authentication failures back off exponentially to five minutes and
reset to the normal 15-second poll after recovery.

## Operations

Inspect the supervisor and recent controller events:

```bash
uv run python paintbot_lab/tools/manage_campaign_order_launch_agent.py status
tail -n 30 "$HOME/Library/Application Support/Stencil Campaign Controller/events.jsonl"
tail -n 30 "$HOME/Library/Application Support/Stencil Campaign Controller/stderr.log"
```

Deliberately restart the managed process:

```bash
launchctl kickstart -k gui/$(id -u)/com.softmax.paintbot-stencil-campaign-controller
```

Reinstall after moving the checkout or recreating `.venv`:

```bash
uv run python paintbot_lab/tools/manage_campaign_order_launch_agent.py install
```

To remove the service while preserving its state and logs:

```bash
uv run python paintbot_lab/tools/manage_campaign_order_launch_agent.py uninstall
```

If the Softmax login expires, authenticate again with the project-local CLI;
the running controller will keep retrying and recover on its next poll:

```bash
uv run softmax login --server https://softmax.com/api
```

## Limitation

This is resilient to controller crashes, logout/login, and machine restart, but
it remains a local service: it cannot issue orders while the Mac is shut down,
asleep, or logged out. After wake or login, `launchd` starts it and the durable
round state lets it resume auditing or arm the next safe directive.
