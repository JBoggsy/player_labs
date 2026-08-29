# Sugarscape longevity policy

This policy treats survival as a bottleneck problem. For every legal destination,
it computes the agent's post-harvest sugar and spice runway in metabolism turns and
maximizes the smaller runway first. Ties prefer balanced reserves, then combined
runway, game-provided welfare, shorter travel, and a stable cell ID.

The policy logs which resource was scarce, why its choice won, and how often it
departed from the built-in greedy candidate. It uses the synchronous WebSocket
client, retries until its first connection succeeds, and exits after that connected
episode closes.

Build from the repository root:

```sh
docker build -f sugarscape_lab/policies/longevity/Dockerfile \
  -t sugarscape-longevity sugarscape_lab/policies/longevity
```
