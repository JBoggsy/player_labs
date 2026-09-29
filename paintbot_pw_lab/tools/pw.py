#!/usr/bin/env python3
"""One entry point for every Paintbot PW lab tool: `pw.py <subcommand> [args]`.

    uv run python paintbot_pw_lab/tools/pw.py tools [--json | --markdown]   # the catalog
    uv run python paintbot_pw_lab/tools/pw.py doctor [--json] [--offline]   # is the lab ready? fixes
    uv run python paintbot_pw_lab/tools/pw.py episodes ROOT --json          # any tool, forwarded
    uv run python paintbot_pw_lab/tools/pw.py <subcommand> --help           # that tool's own help

Every subcommand forwards its arguments unchanged to one tool and returns that tool's exit
code, so the tool's own flags, --json envelope and exit codes apply (docs/tools/README.md
"Agent contract"). `trace` and `map-raw` run the release's Nim binaries from
tools/bin/<tag>/ (a leading `--tag TAG` picks another build).

The catalog (CATALOG below) is the single source for `pw.py tools` and for
docs/tools/README.md, which is generated from it:

    uv run python paintbot_pw_lab/tools/pw.py tools --markdown > paintbot_pw_lab/docs/tools/README.md

Exit codes of `tools`: 0. Of `doctor`: 0 ready; 1 release.env is behind the league (the fix
commands are listed); 2 usage; 3 something is missing (binaries, Python deps, source clone,
login or network), each with the command that fixes it.
"""
from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))
import pw_cli  # noqa: E402
import pw_release  # noqa: E402

LAB = TOOLS.parent
REPO = LAB.parent
DISPATCH = "uv run python paintbot_pw_lab/tools/pw.py"
SKILLS = REPO / ".claude" / "skills"
DEFAULT_CLONE = Path(os.environ.get("PW_CLONE", Path.home() / "coding/coworlds/paintbot-pw"))
TEST_COMMAND = ["uv", "run", "python", "-m", "pytest", "-q", "paintbot_pw_lab/tools/tests", "tools/tests"]
EPISODE_EXITS = ("0 ok; 1 some episodes failed to load or verify (the rest are used, failures listed); "
                 "2 usage error or unknown selector (valid values listed); 3 pw_trace not built "
                 "(run paintbot_pw_lab/tools/build_tools.sh)")
NATIVE_EXITS = ("0 ok; 1 a seat failed to compile or was disabled, or a recording's hash differed; "
                "2 usage error; 3 libpw/paintbot-headless not built or not matching the tag "
                "(run paintbot_pw_lab/tools/build_native.sh)")

# One entry per subcommand. `target` is what the dispatcher runs: ("py", file) forwards to a
# Python tool, ("bin", name) to a release binary, ("sh", script) to a build script,
# ("cmd", argv) to a fixed command. `questions` feed the "which tool answers which question"
# table in docs/tools/README.md. Keep this list and the tools in step: the README test fails
# when the generated file is stale.
CATALOG: list[dict] = [
    {"name": "doctor", "target": ("self", "doctor"),
     "purpose": "Check the lab is ready: release.env vs the league, built binaries and library, Python deps, "
                "source clone, shared skill engines. Prints the exact fix command for each problem.",
     "when_to_use": "First command of any autonomous loop, and whenever a tool exits 3.",
     "questions": ["Is the lab ready to run? What do I fix first?"],
     "inputs": "--json; --offline skips the league check (no network)",
     "outputs": "nothing written; result.checks[] = {name, ok, detail, fix}",
     "exit_codes": "0 ready; 1 release.env behind the league; 2 usage; 3 something missing (fix listed)",
     "doc": "README.md#doctor", "skill": None},
    {"name": "tools", "target": ("self", "tools"),
     "purpose": "Print this catalog (text, --json, or --markdown = docs/tools/README.md).",
     "when_to_use": "To discover which tool answers a question and how to call it.",
     "questions": ["Which tool do I use for X?"],
     "inputs": "--json | --markdown", "outputs": "stdout only", "exit_codes": "0",
     "doc": "README.md", "skill": None},
    {"name": "deployed-ref", "target": ("py", "deployed_ref.py"),
     "purpose": "Compare the league's deployed paintbot-pw build with tools/release.env; --write moves the pin. "
                "Also prints the rule-file diff since the docs' verified commit.",
     "when_to_use": "Before trusting any analysis after a league release; start of every loop (doctor runs it).",
     "questions": ["Which build does the league run? Are our tools and docs current?"],
     "inputs": "--write, --docs-sha SHA, --clone DIR, --json", "outputs": "tools/release.env (only with --write)",
     "exit_codes": "0 current; 1 behind / just written (rebuild next) / untagged; 2 usage; 3 no login, "
                   "network or clone (fix listed)",
     "doc": "deployed_ref.md", "skill": "paintbot-pw-replay"},
    {"name": "release", "target": ("py", "pw_release.py"),
     "purpose": "Print the release pins (tag, sha, docs sha) and which binaries exist for a tag.",
     "when_to_use": "To check a build exists before running a tool (`--require all`).",
     "questions": ["Which tag are the tools pinned to, and is it built?"],
     "inputs": "--tag TAG, --require all|TOOL..., --json", "outputs": "none",
     "exit_codes": "0 ok; 2 unknown tool name; 3 a --require'd binary is missing (build command named)",
     "doc": "pw_release.md", "skill": None},
    {"name": "build", "target": ("sh", "build_tools.sh"),
     "purpose": "Build paintbot-headless, replay_stats, pw_trace and pw_map for the pinned tag (or a given tag).",
     "when_to_use": "When doctor/release reports a missing binary or deployed-ref just moved the pin.",
     "questions": ["How do I build the analysis binaries?"],
     "inputs": "[TAG] (default: tools/release.env)", "outputs": "tools/bin/<tag>/, tools/.cache/<tag>/ worktree",
     "exit_codes": "0 built; non-zero build failure (read the compiler output)",
     "doc": "pw_trace.md", "skill": "paintbot-pw-replay"},
    {"name": "build-native", "target": ("sh", "build_native.sh"),
     "purpose": "Build libpw.dylib (+ libpw.build.json) for local matches; runs build_tools.sh first.",
     "when_to_use": "Before pw_local / pw_tune when the library is missing or the pin moved.",
     "questions": ["How do I build the local match library?"],
     "inputs": "[TAG] (default: tools/release.env)", "outputs": "tools/bin/<tag>/libpw.dylib, libpw.build.json",
     "exit_codes": "0 built; non-zero build failure", "doc": "pw_local.md", "skill": "paintbot-pw-local"},
    {"name": "trace", "target": ("bin", "pw_trace"),
     "purpose": "Hash-checked replay expander (Nim): re-simulates a tape and writes events + sampled state as JSONL.",
     "when_to_use": "Rarely directly; `episodes` runs and caches it. Use for a raw JSONL of one tape.",
     "questions": ["Does this tape replay hash-exactly on our build?"],
     "inputs": "[--tag TAG] REPLAY OUT.jsonl [--state-every N] [--window A:B] [--vis-every M]",
     "outputs": "OUT.jsonl", "exit_codes": "0 verified; 1 hash mismatch or identity failure; 2 bad arguments; "
                                          "3 (dispatcher) binary not built",
     "doc": "pw_trace.md", "skill": "paintbot-pw-replay"},
    {"name": "episodes", "target": ("py", "pw_episodes.py"),
     "purpose": "Load episodes (hosted dirs or local .replay), trace them hash-checked, cache Parquet tables; "
                "--sql queries them with DuckDB.",
     "when_to_use": "First step on any episode data; answering a specific 'what happened at tick X' question.",
     "questions": ["What happened in this match / at tick X?", "Who killed seat 5?",
                   "Does this batch load and verify?"],
     "inputs": "ROOT... [--window A:B] [--vis-every M] [--sql QUERY] [--refresh] [--json]",
     "outputs": "per-episode cache <episode dir>/pw_cache/ or NAME.pw_cache/ beside a .replay (trace.jsonl, "
                "tables/*.parquet, receipt.json); reused while the inputs are unchanged",
     "exit_codes": EPISODE_EXITS, "doc": "pw_episodes.md", "skill": "paintbot-pw-replay"},
    {"name": "metrics", "target": ("py", "pw_metrics.py"),
     "purpose": "Every metric at seat, policy and team level: result, Elo outcome, glory composition, combat, "
                "hearts, idle.",
     "when_to_use": "Summarizing episodes; the numbers behind A/B, mining and diagnosis.",
     "questions": ["Why did we lose this one (glory composition)?", "What is our accuracy / K/D / heart time?"],
     "inputs": "ROOT... [--policy KEY] [--csv DIR] [--json]", "outputs": "with --csv: {seat,policy,team}_metrics.csv",
     "exit_codes": EPISODE_EXITS, "doc": "pw_metrics.md", "skill": "paintbot-pw-replay"},
    {"name": "fights", "target": ("py", "pw_fights.py"),
     "purpose": "Engagements (N-vs-M, who hit first, who won), trades and opening duels per heart contest.",
     "when_to_use": "When combat decides the result: are we losing fights, first shots, or openings?",
     "questions": ["Do we win the fights we take? Who shoots first?", "Who wins the opening duels?"],
     "inputs": "ROOT... [--policy KEY] [--list] [--csv DIR] [--vis-every M] [--json]",
     "outputs": "with --csv: engagements, opening_duels, trades, fight_policy CSVs",
     "exit_codes": EPISODE_EXITS, "doc": "pw_fights.md", "skill": "paintbot-pw-diagnose"},
    {"name": "flags", "target": ("py", "pw_flags.py"),
     "purpose": "Rule-based anomaly flags linked to ticks (stuck, idle, dead VM, died alone, heart lost with "
                "allies, wasted grenade, friendly fire, ...); a policy's losses worst first.",
     "when_to_use": "Triage: which losses to look at first and which ticks in them.",
     "questions": ["What went wrong in our worst losses, and at which tick?", "Is a seat stuck or its VM dead?"],
     "inputs": "ROOT... [--policy KEY] [--flags a,b] [--top N] [--csv FILE] [--json]",
     "outputs": "with --csv: every flag row", "exit_codes": EPISODE_EXITS,
     "doc": "pw_flags.md", "skill": "paintbot-pw-diagnose"},
    {"name": "map", "target": ("py", "pw_mapdata.py"),
     "purpose": "Map geometry (terrain raster, water, trenches, cover, hearts, pickups) cached per release.",
     "when_to_use": "Plots and spatial metrics; check a map loads for a release.",
     "questions": ["Where are the hearts, water, trenches and cover?"],
     "inputs": "[--map NAME] [--rules N] [--step U] [--png OUT] [--json]",
     "outputs": "tools/.cache/maps/<tag>/<map>-r<rules>-s<step>.{npz,json}; --png file",
     "exit_codes": "0 ok; 2 usage or unknown map; 3 pw_map not built (run paintbot_pw_lab/tools/build_tools.sh)",
     "doc": "pw_map.md", "skill": None},
    {"name": "map-raw", "target": ("bin", "pw_map"),
     "purpose": "Raw pw_map export (Nim): OUT_PREFIX.json + .bin (+ .ppm).",
     "when_to_use": "Rarely; `map` caches it.", "questions": [],
     "inputs": "[--tag TAG] OUT_PREFIX [--map NAME] [--rules N] [--step U] [--ppm]", "outputs": "OUT_PREFIX.*",
     "exit_codes": "0 ok; non-zero bad arguments; 3 (dispatcher) binary not built",
     "doc": "pw_map.md", "skill": None},
    {"name": "viz", "target": ("py", "pw_viz.py"),
     "purpose": "Movement diagrams, heatmaps, occupancy comparison, match timeline, GIF (PNG + JSON of the "
                "plotted data).",
     "when_to_use": "To SEE a moment or a habit; always Read the PNG before describing it.",
     "questions": ["Show me seat N's movement from 0:40 to 1:05.", "Where does policy X go / die?",
                   "How do two policies' positions differ?"],
     "inputs": "movement|heatmap|occupancy|timeline|gif ROOT... [--from T --to T] [--seats] [--team] "
               "[--policy] [--out FILE] [--json]",
     "outputs": "default paintbot_pw_lab/analysis/pw_viz/<episode|batch>/<command>[-selectors].png + .json",
     "exit_codes": EPISODE_EXITS + "; a --from past every match end or an unknown policy/seat is exit 2",
     "doc": "pw_viz.md", "skill": "paintbot-pw-replay"},
    {"name": "report", "target": ("py", "pw_match_report.py"),
     "purpose": "One-page Ink & Print HTML match report per episode: result, how it was decided, glory, "
                "timeline, top moments with movement panels, seat table, replay links.",
     "when_to_use": "To hand James one readable page per episode.",
     "questions": ["Give me a one-page report on this match."],
     "inputs": "ROOT... [--out DIR] [--viewer-base URL] [--json]",
     "outputs": "default <episode dir>/pw_report/ (hosted) or NAME.pw_report/ (local): report.html, report.json, "
                "PNGs", "exit_codes": EPISODE_EXITS, "doc": "pw_match_report.md", "skill": "paintbot-pw-replay"},
    {"name": "scout", "target": ("py", "pw_scout.py"),
     "purpose": "Public league survey: fetch recent public episodes (anonymous, gentle), then standings, "
                "matchup matrix, per-policy profiles, shout decoding, flagged episodes.",
     "when_to_use": "Before designing against the field; to profile a specific opponent.",
     "questions": ["Who is strong in the league and how do they play?", "What do opponents shout?"],
     "inputs": "fetch [--max-episodes N] [--out DIR] [--json] | report ROOT... [--ours KEY] [--reasons FILE] "
               "[--json]",
     "outputs": "fetch: episode_data/scout/<date>/r<round>_<ereq>/ + index.json (skips what exists); "
                "report: scout.json, scout.md, scout.interesting.json in the first root",
     "exit_codes": EPISODE_EXITS + "; fetch: 3 when the public API is unreachable",
     "doc": "pw_scout.md", "skill": "paintbot-pw-scout"},
    {"name": "ab-requests", "target": ("py", "pw_ab_requests.py"),
     "purpose": "Compose (never create) the experience-request bodies for a paired / h2h / field A/B.",
     "when_to_use": "Designing a hosted A/B; creating the bodies is a separate step that costs XP credits.",
     "questions": ["Which requests does this A/B need?"],
     "inputs": "--design paired|h2h|field --baseline REF --candidate REF [--opponent REF] [--seeds 1-30] "
               "--league-id ID [--run-id ID] [--out DIR] [--json]",
     "outputs": "with --out: manifest.json + bodies/<label>.json (same --run-id = same bodies)",
     "exit_codes": "0 composed; 2 usage error", "doc": "pw_ab_requests.md", "skill": "paintbot-pw-ab"},
    {"name": "compare", "target": ("py", "compare.py"),
     "purpose": "A/B statistics over hash-checked episodes (paired, h2h, field) on the shared coworld-ab "
                "engines, with SPRT on the Elo outcome.",
     "when_to_use": "Deciding whether a candidate beat its baseline.",
     "questions": ["Did my change help?", "Can we stop the A/B yet (SPRT)?"],
     "inputs": "compare|sprt ROOT... --design D --baseline P --candidate P [--out FILE] [--json]",
     "outputs": "with --out: the full result JSON (with rows), input for compare_report.py",
     "exit_codes": EPISODE_EXITS + "; unknown/ambiguous arm policy or pooled rules versions is exit 2",
     "doc": "compare.md", "skill": "paintbot-pw-ab"},
    {"name": "local", "target": ("py", "pw_local.py"),
     "purpose": "Local BASIC matches on the native library (league glory config, both sides): compile check, "
                "one match, or a seed screen. Screening only.",
     "when_to_use": "Does a candidate compile and run? Is it clearly worse than base? Record a local replay.",
     "questions": ["Does this .bas compile in all 16 seats?", "Is the candidate clearly worse than base locally?"],
     "inputs": "compile FILE | match A B --seed S | screen A B --seeds 1-28 [--out DIR] [--record DIR] [--json]",
     "outputs": "with --out: matches.jsonl + summary.json; with --record: NAME.replay + NAME.meta.json",
     "exit_codes": NATIVE_EXITS, "doc": "pw_local.md", "skill": "paintbot-pw-local"},
    {"name": "tune", "target": ("py", "pw_tune.py"),
     "purpose": "SPSA tuning of @tune integer constants in a .bas against one fixed opponent on local seeds "
                "(resumable log). Screening only.",
     "when_to_use": "A parameter sweep on a candidate; always re-screen on fresh seeds and A/B hosted after.",
     "questions": ["What values of these constants play best locally?"],
     "inputs": "knobs FILE | run CAND OPP --seeds --iterations --log FILE [--out TUNED.bas] | render CAND "
               "--log FILE --out FILE; [--json]",
     "outputs": "the JSONL log (append-only, resumable), the tuned .bas",
     "exit_codes": NATIVE_EXITS, "doc": "pw_tune.md", "skill": "paintbot-pw-tune"},
    {"name": "intent", "target": ("py", "pw_intent.py"),
     "purpose": "Intent telemetry: record local episodes with seat logs, show PWI lines, audit intent/belief "
                "against the replay.",
     "when_to_use": "When the question is what our policy MEANT to do (heart choice, target, reason).",
     "questions": ["What was our policy trying to do at tick X?", "Where did its belief differ from reality?"],
     "inputs": "record A B --seeds S | show ROOT... | audit ROOT...; [--json]",
     "outputs": "default paintbot_pw_lab/analysis/pw_intent/{episodes,audit}/",
     "exit_codes": "0 ok; 1 some episodes failed to record or load; 2 usage; 3 pw_trace or the handoff engine "
                   "not built (run paintbot_pw_lab/tools/build_tools.sh)",
     "doc": "pw_intent.md", "skill": "paintbot-pw-diagnose"},
    {"name": "miner", "target": ("py", "miner_rows.py"),
     "purpose": "Rows for the coworld-hypothesis-miner: one per (episode, our policy) from metrics, fights, "
                "flags and intent.",
     "when_to_use": "Nothing specific is suspected: mine a batch for what separates good matches from bad.",
     "questions": ["What should we improve next?", "Which behavior costs us points?"],
     "inputs": "ROOT... --policy KEY [--score elo|win] --out FILE [--json]",
     "outputs": "the JSONL rows file", "exit_codes": EPISODE_EXITS + "; no/unknown --policy is exit 2 listing them",
     "doc": "features.md", "skill": "paintbot-pw-diagnose"},
    {"name": "mine", "target": ("cmd", ["{python}", str(SKILLS / "coworld-hypothesis-miner" / "scripts" /
                                                        "mine_hypotheses.py"),
                                        "--adapter", str(TOOLS / "features.py")]),
     "purpose": "Run the shared hypothesis miner on miner rows with the lab's features.py adapter.",
     "when_to_use": "Right after `miner` wrote rows.", "questions": [],
     "inputs": "--rows FILE [--top N] [--out FILE] [--json FILE] (shared engine's flags; adapter preset)",
     "outputs": "Markdown ranking (stdout or --out); --json FILE: association table",
     "exit_codes": "the shared engine's (0 ok, non-zero on error); not the lab envelope",
     "doc": "features.md", "skill": "paintbot-pw-diagnose"},
    {"name": "winprob", "target": ("py", "pw_winprob.py"),
     "purpose": "Win-probability model P(win | team state at t), held-out evaluation, and per-event credit "
                "(captures, kills, deaths).",
     "when_to_use": "Which events actually swing matches; crediting a batch with a saved model.",
     "questions": ["Which captures/kills swing win probability most?", "When did we lose this match?"],
     "inputs": "fetch --out DIR | fit ROOT... --out DIR | credit ROOT... --model FILE --out DIR; [--json]",
     "outputs": "fit: model.json, report.json, wp_{ticks,events,policy}.parquet; fetch: <ereq>/ dirs (skips "
                "what exists)",
     "exit_codes": EPISODE_EXITS + "; fit with < 4 usable episodes is exit 1; fetch: 3 when the API is unreachable",
     "doc": "pw_winprob.md", "skill": "paintbot-pw-diagnose"},
    {"name": "test", "target": ("cmd", TEST_COMMAND),
     "purpose": "Run the lab tool tests (and the repo's shared analysis tests).",
     "when_to_use": "After changing a tool.", "questions": ["Do the tools still pass their tests?"],
     "inputs": "extra pytest args", "outputs": "none", "exit_codes": "pytest's (0 all passed)",
     "doc": "README.md", "skill": None},
]
REFERENCE_DOCS = [
    ("tables.md", "The table contract: every Parquet table and column pw_episodes writes."),
    ("pw_release.md", "Release pins: tools/release.env and pw_release.py."),
]
BY_NAME = {entry["name"]: entry for entry in CATALOG}


# ---------------------------------------------------------------- catalog output

def command_of(entry: dict) -> str:
    return f"{DISPATCH} {entry['name']}"


def public_entry(entry: dict) -> dict:
    """A catalog row as `tools --json` prints it."""
    kind, what = entry["target"]
    runs = {"py": f"paintbot_pw_lab/tools/{what}", "sh": f"paintbot_pw_lab/tools/{what}",
            "bin": f"paintbot_pw_lab/tools/bin/<tag>/{what}", "self": "pw.py",
            "cmd": " ".join(Path(a).relative_to(REPO).as_posix() if a.startswith(str(REPO)) else a
                            for a in what)}[kind]
    return {"name": entry["name"], "command": command_of(entry), "runs": runs, "purpose": entry["purpose"],
            "when_to_use": entry["when_to_use"], "questions": entry["questions"], "inputs": entry["inputs"],
            "outputs": entry["outputs"], "exit_codes": entry["exit_codes"],
            "json_envelope": kind == "py" or kind == "self",
            "doc": f"paintbot_pw_lab/docs/tools/{entry['doc']}",
            "skill": f"paintbot_pw_lab/.claude/skills/{entry['skill']}/SKILL.md" if entry["skill"] else None}


def _cell(text: str) -> str:
    return str(text).replace("|", "\\|").replace("\n", " ")


def markdown() -> str:
    """docs/tools/README.md, generated from CATALOG."""
    lines = [
        "# Paintbot PW lab tools",
        "",
        "<!-- GENERATED by `uv run python paintbot_pw_lab/tools/pw.py tools --markdown > "
        "paintbot_pw_lab/docs/tools/README.md`. Edit CATALOG in tools/pw.py, not this file; "
        "tools/tests/test_pw_dispatch.py fails when it is stale. -->",
        "",
        "Every tool runs through one dispatcher from the repo root (`personal_labs_paintbot_pw/`):",
        "",
        "```bash",
        f"{DISPATCH} doctor --json          # is the lab ready? each problem comes with its fix command",
        f"{DISPATCH} tools --json           # this catalog, machine-readable",
        f"{DISPATCH} <subcommand> [args]    # forwards to the tool; its flags, --json and exit codes apply",
        f"{DISPATCH} <subcommand> --help    # every flag, with examples",
        "```",
        "",
        "## Which tool answers which question",
        "",
        "| Question | Subcommand | Skill |",
        "| --- | --- | --- |",
    ]
    for entry in CATALOG:
        for question in entry["questions"]:
            skill = f"`{entry['skill']}`" if entry["skill"] else ""
            lines.append(f"| {_cell(question)} | `{entry['name']}` | {skill} |")
    lines += ["", "## Tools", ""]
    for entry in CATALOG:
        row = public_entry(entry)
        lines += [
            f"### {entry['name']}",
            "",
            f"{entry['purpose']}",
            "",
            f"- **Command:** `{row['command']}` (runs `{row['runs']}`)",
            f"- **When:** {entry['when_to_use']}",
            f"- **Inputs:** {entry['inputs']}",
            f"- **Outputs:** {entry['outputs']}",
            f"- **Exit codes:** {entry['exit_codes']}",
            f"- **Reference:** [{entry['doc']}]({entry['doc']})"
            + (f"; skill [`{entry['skill']}`](../../.claude/skills/{entry['skill']}/SKILL.md)" if entry["skill"] else ""),
            "",
        ]
    lines += ["## Reference docs", ""]
    lines += [f"- [{name}]({name}): {text}" for name, text in REFERENCE_DOCS]
    lines += ["", *AGENT_CONTRACT.splitlines(), ""]
    return "\n".join(lines)


AGENT_CONTRACT = """## Agent contract

Every Python tool (all subcommands above except `build`, `build-native`, `trace`, `map-raw`,
`mine` and `test`) follows one contract, implemented once in `tools/pw_cli.py`:

1. **Non-interactive.** `--help` documents every flag and ends with examples and the exit codes.
2. **`--json`** prints exactly ONE JSON object to stdout; all human-readable text (and anything
   native code or child processes print) goes to stderr. Keys:

   | Key | Meaning |
   | --- | --- |
   | `ok` | `true` exactly when the exit code is 0 |
   | `tool` | the tool name (`pw_metrics`, ...) |
   | `release_tag` | the engine build used (`--tag`, else `tools/release.env`) |
   | `inputs` | the parsed arguments |
   | `outputs` | every path the run wrote (caches the run created included) |
   | `counts` | `processed`, `failed`, `excluded`, plus tool-specific counts |
   | `failures` | `[{id, code, message}]`: one per failed episode, seat, or the usage/environment error |
   | `result` | the tool's payload (or a path to it) |
   | `next` | suggested follow-up commands; on exit 3, the fix command |

3. **Exit codes:** `0` success; `1` some inputs failed verification or loading (partial results
   are still written, failures listed); `2` usage or config error; `3` environment missing
   (binary, library or release not built), and the message names the exact fixing command,
   for example `paintbot_pw_lab/tools/build_tools.sh`.
4. **Deterministic outputs, idempotent re-runs.** Default output locations are documented per
   tool; files a tool writes without `--out` go under `paintbot_pw_lab/analysis/<tool>/` or next to
   the episode, at paths that depend only on the inputs. Traces and map rasters are cached
   (receipt-checked), public fetches skip episodes already on disk.
5. **Unknown selectors are usage errors.** A policy, seat, flag or metric name that is not in the
   data, or a time window past the end of every match, exits 2 and lists the valid values
   (`result.valid` in `--json`). An empty output never means success.

A loop reads the envelope like this:

```python
proc = subprocess.run([... , "--json"], capture_output=True, text=True)
env = json.loads(proc.stdout)
if proc.returncode == 3: run env["next"][0], then retry        # build / login / network
elif proc.returncode == 2: fix the arguments (env["failures"][0]["message"], env["result"]["valid"])
elif proc.returncode == 1: use env["result"], but report env["failures"]; never quote a failed episode
else: use env["result"]; env["next"] suggests the follow-up
```

### doctor

`pw.py doctor` runs these checks and lists a fix for each failure: Python dependencies in the
uv environment (`uv sync`), `tools/release.env` readable, every binary and the native library
for the pinned tag (`build_tools.sh` / `build_native.sh`), the library's build receipt matching
the tag, the paintbot-pw source clone (`git clone ...`), the shared skill engines (`ab_stats`,
`paired_stats`, `variance_miner`), and, unless `--offline`, `deployed_ref.py` (league build vs
`release.env`; needs `softmax login` and network)."""


def cmd_tools(argv: list[str]) -> int:
    if "--markdown" in argv:
        sys.stdout.write(markdown())
        return 0
    rows = [public_entry(e) for e in CATALOG]
    if "--json" in argv:
        print(json.dumps({"ok": True, "tool": "pw", "release_tag": pw_cli._release_tag(), "inputs": {"command": "tools"},
                          "outputs": [], "counts": {"processed": len(rows), "failed": 0, "excluded": 0},
                          "failures": [], "result": {"tools": rows, "contract": "paintbot_pw_lab/docs/tools/README.md"
                                                                                "#agent-contract"},
                          "next": [f"{DISPATCH} doctor --json"]}))
        return 0
    for row in rows:
        print(f"{row['name']:<13} {row['purpose']}")
        print(f"{'':<13} when: {row['when_to_use']}")
    print(f"\n{DISPATCH} <subcommand> --help for flags; {DISPATCH} tools --json for the full catalog")
    return 0


# ---------------------------------------------------------------- doctor

DEPENDENCIES = ("numpy", "pandas", "pyarrow", "duckdb", "matplotlib", "sklearn", "scipy", "httpx", "PIL")


def check(name: str, ok: bool, detail: str, fix: str | None = None, severity: str = "missing") -> dict:
    return {"name": name, "ok": ok, "detail": detail, "fix": None if ok else fix, "severity": None if ok else severity}


def doctor_checks(offline: bool) -> list[dict]:
    checks = []
    missing = [m for m in DEPENDENCIES if importlib.util.find_spec(m) is None]
    in_venv = sys.prefix != getattr(sys, "base_prefix", sys.prefix)
    checks.append(check("python_env", not missing and in_venv,
                        f"{sys.executable}; missing {missing}" if missing else
                        f"{sys.executable} ({'uv venv' if in_venv else 'NOT a venv: run through uv'})",
                        "uv sync   (then run tools with `uv run python ...`)"))
    checks.append(check("uv", shutil.which("uv") is not None, shutil.which("uv") or "uv not on PATH",
                        "install uv: https://docs.astral.sh/uv/getting-started/installation/"))
    try:
        env = pw_release.read_env()
        tag = env["PW_RELEASE_TAG"]
        checks.append(check("release_env", True, f"{tag} {env['PW_RELEASE_SHA']} (docs {env['PW_DOCS_SHA']})"))
    except (OSError, ValueError) as err:
        checks.append(check("release_env", False, str(err), f"restore {pw_release.RELEASE_ENV} from git"))
        return checks
    for tool in pw_release.BUILT_BY:
        path = pw_release.bin_dir(tag) / tool
        checks.append(check(f"built:{tool}", path.is_file(), str(path), pw_release.build_command(tool)))
    receipt = pw_release.bin_dir(tag) / "libpw.build.json"
    if receipt.is_file():
        built_for = json.loads(receipt.read_text()).get("tag")
        checks.append(check("libpw_receipt", built_for == tag, f"libpw built for {built_for}",
                            pw_release.build_command("libpw.dylib")))
    clone = DEFAULT_CLONE
    checks.append(check("source_clone", (clone / ".git").exists(), str(clone),
                        f"git clone https://github.com/Metta-AI/paintbot-pw {clone}"))
    for script in ("coworld-ab/scripts/ab_stats.py", "coworld-ab/scripts/paired_stats.py",
                   "coworld-hypothesis-miner/scripts/variance_miner.py"):
        path = SKILLS / script
        checks.append(check(f"shared:{Path(script).stem}", path.is_file(), str(path.relative_to(REPO)),
                            "restore the shared skill from git (git checkout -- .claude/skills)"))
    if offline:
        checks.append(check("league_build", True, "skipped (--offline)"))
    else:
        checks.append(league_check())
    return checks


def league_check() -> dict:
    """deployed_ref.py --json: 0 current, 1 behind (fix = its next commands), 3 environment."""
    proc = subprocess.run([sys.executable, str(TOOLS / "deployed_ref.py"), "--json"], capture_output=True, text=True)
    try:
        envelope = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return check("league_build", False, f"deployed_ref.py exit {proc.returncode}: {proc.stderr.strip()[-300:]}",
                     f"{DISPATCH} deployed-ref")
    if proc.returncode == 0:
        tracked = envelope["result"]["tracked"]
        changed = envelope["result"]["docs_rule_files_changed"]
        return check("league_build", True, f"league on {tracked['tag']} {tracked['sha'][:8]}; tools current; "
                                           f"{changed} rule-bearing file(s) changed since the docs' commit")
    if proc.returncode == 1:
        return check("league_build", False, "; ".join(f["message"] for f in envelope["failures"])
                     or "release.env is behind the league's build",
                     " && ".join(envelope["next"][:3]) or f"{DISPATCH} deployed-ref --write", severity="stale")
    message = "; ".join(f["message"] for f in envelope["failures"]) or proc.stderr.strip()[-300:]
    return check("league_build", False, message, (envelope.get("next") or ["uv run softmax login"])[0])


def cmd_doctor(argv: list[str]) -> int:
    parser = pw_cli.ArgumentParser("pw_doctor", "Check the lab is ready and print the fix for each problem.",
                                   prog="pw.py doctor", examples=[f"{DISPATCH} doctor --json",
                                                                  f"{DISPATCH} doctor --offline"],
                                   exit_codes="0 ready; 1 release.env behind the league; 2 usage; "
                                              "3 something missing (fix listed)")
    parser.add_argument("--offline", action="store_true", help="skip the league check (no network, no login)")

    def run_cli(args, report):
        checks = doctor_checks(args.offline)
        for c in checks:
            mark = "ok  " if c["ok"] else ("STALE" if c["severity"] == "stale" else "FAIL")
            print(f"{mark} {c['name']:<22} {c['detail']}")
            if not c["ok"]:
                print(f"     fix: {c['fix']}")
                report.fail(c["name"], "stale" if c["severity"] == "stale" else "environment_missing", c["detail"])
                report.suggest(c["fix"])
        report.counts["processed"] = len(checks)
        if any(not c["ok"] and c["severity"] == "missing" for c in checks):
            report.exit_code = pw_cli.EXIT_ENVIRONMENT
        elif any(not c["ok"] for c in checks):
            report.exit_code = pw_cli.EXIT_PARTIAL
        if report.exit_code is None:
            print("READY")
        return {"checks": checks}

    return pw_cli.run(parser, run_cli, argv)


# ---------------------------------------------------------------- forwarding

def forward(entry: dict, argv: list[str]) -> int:
    kind, what = entry["target"]
    if kind == "py":
        return subprocess.call([sys.executable, str(TOOLS / what), *argv])
    if kind == "sh":
        return subprocess.call([str(TOOLS / what), *argv])
    if kind == "cmd":
        return subprocess.call([sys.executable if a == "{python}" else a for a in what] + argv, cwd=REPO)
    tag = None
    if argv[:1] == ["--tag"] and len(argv) >= 2:
        tag, argv = argv[1], argv[2:]
    try:
        binary = pw_release.require_built(what, tag)
    except pw_release.NotBuilt as err:
        print(f"ERROR: {err}", file=sys.stderr)
        if "--json" in argv:   # the binary itself has no envelope; the dispatcher's refusal does
            report = pw_cli.Report(what, json_mode=True)
            report.release_tag = tag or report.release_tag
            report.fail(err.tool, "not_built", str(err))
            report.suggest(err.fix)
            print(json.dumps(report.envelope(pw_cli.EXIT_ENVIRONMENT)))
        return pw_cli.EXIT_ENVIRONMENT
    return subprocess.call([str(binary), *argv])


def usage() -> str:
    names = ", ".join(e["name"] for e in CATALOG)
    return f"usage: pw.py <subcommand> [args]   subcommands: {names}\n{DISPATCH} tools   lists what each one does"


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        print(usage())
        return 0 if argv else pw_cli.EXIT_USAGE
    name, rest = argv[0], argv[1:]
    if name == "tools":
        return cmd_tools(rest)
    if name == "doctor":
        return cmd_doctor(rest)
    entry = BY_NAME.get(name)
    if entry is None:
        message = f"unknown subcommand {name!r}; valid: {', '.join(BY_NAME)}"
        if "--json" in rest:
            print(json.dumps({"ok": False, "tool": "pw", "release_tag": pw_cli._release_tag(),
                              "inputs": {"argv": argv}, "outputs": [],
                              "counts": {"processed": 0, "failed": 1, "excluded": 0},
                              "failures": [{"id": "usage", "code": "usage_error", "message": message}],
                              "result": {"valid": list(BY_NAME)}, "next": [f"{DISPATCH} tools --json"]}))
        print(message, file=sys.stderr)
        return pw_cli.EXIT_USAGE
    return forward(entry, rest)


if __name__ == "__main__":
    sys.exit(main())
