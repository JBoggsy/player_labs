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

If an outage spans the short pending-order window, the controller recovers from
the settled round in campaign frame history. It verifies the recorded orders
and battle metadata against the saved directive, audits the historical
settlement, removes the stale prompt block, and resumes with the next round.

## Statistical order selection

Every poll resolves the player's active champion membership. A champion-version
change causes an immediate full refresh; otherwise the controller refreshes XP
evidence every 60 seconds and campaign evidence after each settled round. The
version-filtered episode-request feed supplies all completed Paintbot episodes
for that champion. Commissioner rows are joined to the player's full campaign
history, while non-commissioner rows are retained only when their requester is
the logged-in user's `mine` identity. Failed episodes and rows without an
unambiguous subject score are excluded.

Evidence is bucketed by `(opponent player id, map_ref, campaign mode)`. Each
bucket records campaign and XP counts separately, then computes:

- the Beta(1,1)-prior posterior mean of `P(win | opponent, cell type)`;
- the posterior predictive probability of winning both captain-swapped games,
  `E[p^2]`;
- a 95% Wilson interval as a sensitivity statistic.

The airdrop chooses the non-FFA target with the highest predicted double-win
probability, falling back to the historical opponent order only when estimates
tie. In addition, the controller issues one adjacent cell-to-cell invasion when
an exact opponent/cell bucket has `E[p^2] > 0.75`; exactly 75% does not qualify.
The source must still be ours and orthogonally adjacent when the prompt is
installed. Both tool calls, resulting orders, battles, and settlements are
audited and activation details are written to `events.jsonl`. Full analysis,
including source counts and every matchup bucket, is persisted in `state.json`.

## Operations

Inspect the supervisor and recent controller events:

```bash
uv run python paintbot_lab/tools/manage_campaign_order_launch_agent.py status
tail -n 30 "$HOME/Library/Application Support/Stencil Campaign Controller/events.jsonl"
tail -n 30 "$HOME/Library/Application Support/Stencil Campaign Controller/stderr.log"
```

Inspect the current champion and statistical evidence:

```bash
jq '.analysis | {champion, refreshed_at, sources, buckets}' \
  "$HOME/Library/Application Support/Stencil Campaign Controller/state.json"
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
