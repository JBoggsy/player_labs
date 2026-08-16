#!/usr/bin/env python3
"""Serve a read-only dashboard for one Paintbot RL training workspace."""

from __future__ import annotations

import argparse
import json
import math
import re
import shutil
import subprocess
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Callable


LOSS_RE = re.compile(r"epoch=(\d+) step=(\d+) loss=([0-9.eE+-]+)")
VALIDATION_RE = re.compile(r"epoch=(\d+) validation_loss=([0-9.eE+-]+)")
ERROR_RE = re.compile(
    r"traceback|runtimeerror|out of memory|cuda.*error|no space|killed|\bnan\b|failed",
    re.IGNORECASE,
)
METRIC_KEYS = (
    "samples",
    "mean_loss",
    "constrained_token_accuracy",
    "constrained_exact_action_accuracy",
    "autoregressive_exact_action_accuracy",
    "changed_action_samples",
    "constrained_changed_exact_action_accuracy",
    "autoregressive_changed_exact_action_accuracy",
    "changed_component_accuracy",
    "change_precision",
    "change_recall",
    "previous_mask_exact_action_accuracy",
)
PROGRESS_RATE_POINTS: dict[str, list[tuple[float, int]]] = {}


def read_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text())
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}
    return value if isinstance(value, dict) else {}


def read_tail(path: Path, byte_limit: int = 2_000_000) -> str:
    try:
        with path.open("rb") as source:
            source.seek(0, 2)
            size = source.tell()
            source.seek(max(0, size - byte_limit))
            data = source.read()
    except OSError:
        return ""
    if size > byte_limit:
        data = data.split(b"\n", 1)[-1]
    return data.decode("utf-8", errors="replace")


def parse_training_log(text: str, point_limit: int = 500) -> dict:
    losses = [
        {"epoch": int(epoch), "step": int(step), "loss": float(loss)}
        for epoch, step, loss in LOSS_RE.findall(text)
    ]
    validations = [
        {"epoch": int(epoch), "loss": float(loss)}
        for epoch, loss in VALIDATION_RE.findall(text)
    ]
    errors = [line.strip() for line in text.splitlines() if ERROR_RE.search(line)]
    return {
        "losses": losses[-point_limit:],
        "validations": validations,
        "errors": errors[-20:],
        "latest": losses[-1] if losses else None,
    }


def full_training_log(text: str, marker: str = "training-v1/full") -> str:
    """Exclude canary output when the shared log still contains both runs."""
    lines = text.splitlines()
    starts = [
        index
        for index, line in enumerate(lines)
        if "train_sft.py" in line and marker in line
    ]
    return "\n".join(lines[starts[-1] :]) if starts else text


def run_text(command: list[str]) -> str:
    try:
        return subprocess.run(
            command, check=False, capture_output=True, text=True, timeout=5
        ).stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        return ""


def process_snapshot(run: Callable[[list[str]], str]) -> dict:
    text = run(
        [
            "pgrep",
            "-af",
            "run_(expert_training|diversity_experiment|event_action_experiment|spatial_semantics_experiment).py|train_sft.py|evaluate_(event_)?sft.py|supervise_(expert_training|diversity_experiment|accuracy_experiments)",
        ]
    )
    lines = [line for line in text.splitlines() if "training_dashboard.py" not in line]
    return {
        "trainer": any("train_sft.py" in line for line in lines),
        "evaluator": any(
            "evaluate_sft.py" in line or "evaluate_event_sft.py" in line
            for line in lines
        ),
        "supervisor": any("supervise_" in line for line in lines),
        "handoff": any("run_" in line and "training_dashboard.py" not in line for line in lines),
        "lines": lines,
    }


def gpu_snapshot(run: Callable[[list[str]], str]) -> dict:
    text = run(
        [
            "nvidia-smi",
            "--query-gpu=name,memory.used,memory.total,utilization.gpu,temperature.gpu",
            "--format=csv,noheader,nounits",
        ]
    )
    if not text:
        return {}
    values = [value.strip() for value in text.splitlines()[0].split(",")]
    if len(values) != 5:
        return {"raw": text}
    try:
        return {
            "name": values[0],
            "memory_used_mib": int(values[1]),
            "memory_total_mib": int(values[2]),
            "utilization_percent": int(values[3]),
            "temperature_c": int(values[4]),
        }
    except ValueError:
        return {"raw": text}


def checkpoint_states(output: Path, steps_per_epoch: int) -> list[dict]:
    states = []
    for path in (output / "trainer_state").glob("*/training_state.json"):
        value = read_json(path)
        if not value:
            continue
        completed_epochs = int(value.get("completed_epochs", 0))
        completed_batches = int(value.get("completed_batches_in_epoch", 0))
        states.append(
            {
                "name": path.parent.name,
                "mtime": path.stat().st_mtime,
                "global_updates": int(value.get("global_updates", 0)),
                "completed_epochs": completed_epochs,
                "completed_batches_in_epoch": completed_batches,
                "completed_microbatches": completed_epochs * steps_per_epoch
                + completed_batches,
                "best_validation_loss": value.get("best_validation_loss"),
                "best_epoch": value.get("best_epoch"),
            }
        )
    return sorted(states, key=lambda item: item["mtime"])


def estimate_eta(points: list[tuple[float, int]], remaining: int) -> dict:
    points = sorted(set(points))[-8:]
    if remaining <= 0:
        return {"seconds": 0, "rate_per_second": None}
    if len(points) < 2 or points[-1][1] <= points[0][1]:
        return {"seconds": None, "rate_per_second": None}
    rate = (points[-1][1] - points[0][1]) / (points[-1][0] - points[0][0])
    return {
        "seconds": remaining / rate if rate > 0 else None,
        "rate_per_second": rate if rate > 0 else None,
    }


def observed_progress_points(key: str, now: float, completed: int) -> list[tuple[float, int]]:
    points = PROGRESS_RATE_POINTS.setdefault(key, [])
    if points and completed < points[-1][1]:
        points.clear()
    if not points or completed > points[-1][1]:
        points.append((now, completed))
        del points[:-8]
    return points


def evaluation_metrics(output: Path) -> dict:
    result = {}
    for path in sorted(output.glob("*evaluation.json")):
        evaluation = read_json(path)
        group = evaluation.get("groups", {}).get("all", {})
        result[path.name] = {
            **{key: group.get(key) for key in METRIC_KEYS},
            "autoregressive_exact_action_cluster_bootstrap": evaluation.get(
                "autoregressive_exact_action_cluster_bootstrap"
            ),
        }
    return result


def build_snapshot(
    workspace: Path,
    run: Callable[[list[str]], str] = run_text,
    *,
    training_root: Path | None = None,
    log_path: Path | None = None,
) -> dict:
    training_root = training_root or workspace / "training-v1"
    output = training_root / "full"
    status = read_json(training_root / "status.json")
    if log_path is None:
        log_path = workspace.parent.parent / "logs" / "expert-training-v1.log"
        if not log_path.exists():
            log_path = workspace / "logs" / "expert-training-v1.log"
    log = parse_training_log(
        full_training_log(read_tail(log_path), f"{training_root.name}/full")
    )
    processes = process_snapshot(run)

    train_budget = int(status.get("train_budget", 250_000))
    epochs = int(status.get("epochs", 3))
    batch_size = 2
    for line in processes["lines"]:
        match = re.search(r"--batch-size\s+(\d+)", line)
        if match:
            batch_size = int(match.group(1))
            break
    steps_per_epoch = math.ceil(train_budget / batch_size)
    total_microbatches = epochs * steps_per_epoch
    latest = log["latest"]
    completed = 0
    current_epoch = 0
    current_step = 0
    if latest:
        current_epoch = latest["epoch"]
        current_step = latest["step"]
        completed = (current_epoch - 1) * steps_per_epoch + current_step
    states = checkpoint_states(output, steps_per_epoch)
    if states and states[-1]["completed_microbatches"] > completed:
        completed = states[-1]["completed_microbatches"]
        current_epoch = states[-1]["completed_epochs"]
        current_step = states[-1]["completed_batches_in_epoch"]
    if status.get("stage") == "complete":
        completed = total_microbatches

    now = time.time()
    rate_points = [
        (item["mtime"], item["completed_microbatches"])
        for item in states
        if item["completed_microbatches"]
    ]
    if latest and log_path.exists():
        rate_points.append((log_path.stat().st_mtime, completed))
    rate_points.extend(observed_progress_points(str(training_root), now, completed))
    eta = estimate_eta(rate_points, max(0, total_microbatches - completed))
    disk = shutil.disk_usage(workspace)
    training_run = read_json(output / "training_run.json")
    validation_history = list(log["validations"])
    if training_run:
        validation_history = [
            {"epoch": int(item["epoch"]), "loss": float(item["validation_loss"])}
            for item in training_run.get("history", [])
            if "validation_loss" in item
        ]
    corpus = read_json(workspace / "prepared" / "provenance.json")

    stage = str(status.get("stage", ""))
    if stage in {"training_canary", "training_full"}:
        expected_process = processes["trainer"]
    elif stage.startswith("evaluating_"):
        expected_process = processes["evaluator"]
    elif stage == "complete":
        expected_process = True
    else:
        expected_process = processes["handoff"] or processes["supervisor"]
    healthy = not log["errors"] and expected_process
    return {
        "generated_at_unix": now,
        "status": status,
        "healthy": healthy,
        "progress": {
            "epoch": current_epoch,
            "step": current_step,
            "steps_per_epoch": steps_per_epoch,
            "epochs": epochs,
            "completed_microbatches": completed,
            "total_microbatches": total_microbatches,
            "fraction": completed / total_microbatches if total_microbatches else 0,
            "eta_seconds": eta["seconds"],
            "microbatches_per_second": eta["rate_per_second"],
        },
        "validation_history": validation_history,
        "recent_losses": log["losses"],
        "training_run": {
            key: training_run.get(key)
            for key in (
                "best_validation_loss",
                "best_epoch",
                "duration_seconds",
                "samples",
                "validation_samples",
            )
        }
        if training_run
        else {},
        "evaluations": evaluation_metrics(output),
        "checkpoints": states[-12:],
        "processes": processes,
        "gpu": gpu_snapshot(run),
        "disk": {
            "free_bytes": disk.free,
            "total_bytes": disk.total,
            "used_fraction": disk.used / disk.total,
        },
        "corpus": {
            "split_counts": corpus.get("split_counts", {}),
            "failures": corpus.get("failures"),
        },
        "errors": log["errors"],
    }


HTML = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Paintbot RL Training</title><style>
:root{color-scheme:dark;--bg:#0b0f14;--panel:#121923;--line:#273243;--text:#e8edf5;--muted:#8f9bad;--good:#54d69b;--warn:#f2c96d;--bad:#ff6b73;--blue:#6aa9ff}
*{box-sizing:border-box}body{margin:0;background:radial-gradient(circle at 20% 0,#172238 0,#0b0f14 42%);color:var(--text);font:14px ui-monospace,SFMono-Regular,Menlo,monospace}
main{max-width:1240px;margin:auto;padding:28px}.top{display:flex;justify-content:space-between;gap:24px;align-items:end}h1{font:700 29px system-ui;margin:0 0 6px}.muted{color:var(--muted)}.pill{padding:7px 11px;border:1px solid var(--line);border-radius:999px}.good{color:var(--good)}.bad{color:var(--bad)}
.grid{display:grid;grid-template-columns:repeat(12,1fr);gap:14px;margin-top:18px}.card{background:rgba(18,25,35,.92);border:1px solid var(--line);border-radius:13px;padding:17px;box-shadow:0 14px 40px #0004}.span3{grid-column:span 3}.span4{grid-column:span 4}.span6{grid-column:span 6}.span8{grid-column:span 8}.span12{grid-column:span 12}
.label{text-transform:uppercase;letter-spacing:.08em;color:var(--muted);font-size:11px}.value{font:650 25px system-ui;margin-top:8px}.bar{height:9px;background:#222c3b;border-radius:6px;overflow:hidden;margin-top:14px}.bar>i{display:block;height:100%;background:linear-gradient(90deg,var(--blue),var(--good));width:0}.metric-row{display:flex;justify-content:space-between;border-bottom:1px solid #202a38;padding:9px 0}.metric-row:last-child{border:0}canvas{width:100%;height:235px}.error{white-space:pre-wrap;color:var(--bad);max-height:180px;overflow:auto}.hidden{display:none}table{width:100%;border-collapse:collapse}td,th{text-align:left;padding:8px;border-bottom:1px solid #202a38}th{color:var(--muted);font-weight:500}
@media(max-width:800px){.span3,.span4,.span6,.span8{grid-column:span 12}.top{align-items:start;flex-direction:column}}
</style></head><body><main>
<div class="top"><div><h1>Paintbot RL Training</h1><div class="muted" id="stage">Connecting…</div></div><div class="pill" id="freshness">—</div></div>
<section class="grid">
<div class="card span6"><div class="label">Run progress</div><div class="value" id="progress">—</div><div class="bar"><i id="progressBar"></i></div><div class="muted" style="margin-top:11px" id="eta">—</div></div>
<div class="card span3"><div class="label">GPU</div><div class="value" id="gpu">—</div><div class="muted" id="gpuSub">—</div></div>
<div class="card span3"><div class="label">Disk free</div><div class="value" id="disk">—</div><div class="muted" id="diskSub">—</div></div>
<div class="card span8"><div class="label">Recent training loss</div><canvas id="lossChart"></canvas></div>
<div class="card span4"><div class="label">Validation loss</div><div id="validations" style="margin-top:8px">—</div></div>
<div class="card span6"><div class="label">Checkpoints</div><div id="checkpoints" style="margin-top:8px">—</div></div>
<div class="card span6"><div class="label">Detailed evaluation</div><div id="evaluation" style="margin-top:8px">Available after final evaluation.</div></div>
<div class="card span12 hidden" id="errorCard"><div class="label">Errors requiring attention</div><div class="error" id="errors"></div></div>
</section></main><script>
const $=id=>document.getElementById(id), pct=x=>(100*x).toFixed(1)+'%', num=x=>x==null?'—':Number(x).toLocaleString(), gib=x=>(x/1073741824).toFixed(0)+' GiB';
function duration(s){if(s==null)return 'ETA unavailable';s=Math.max(0,s);const h=Math.floor(s/3600),m=Math.floor((s%3600)/60);return h?`${h}h ${m}m remaining`:`${m}m remaining`}
function metric(label,value,percent=false){let v=value==null?'—':typeof value==='string'?value:percent?pct(value):num(value);return `<div class="metric-row"><span class="muted">${label}</span><span>${v}</span></div>`}
function chart(points){const c=$('lossChart'),d=devicePixelRatio||1,w=c.clientWidth,h=c.clientHeight;c.width=w*d;c.height=h*d;const x=c.getContext('2d');x.scale(d,d);x.clearRect(0,0,w,h);if(points.length<2)return;const vals=points.map(p=>p.loss),lo=Math.min(...vals),hi=Math.max(...vals),pad=18;x.strokeStyle='#273243';x.beginPath();x.moveTo(pad,h-pad);x.lineTo(w-pad,h-pad);x.stroke();x.strokeStyle='#6aa9ff';x.lineWidth=1.6;x.beginPath();points.forEach((p,i)=>{const xx=pad+i*(w-2*pad)/(points.length-1),yy=h-pad-(p.loss-lo)/(hi-lo||1)*(h-2*pad);i?x.lineTo(xx,yy):x.moveTo(xx,yy)});x.stroke();x.fillStyle='#8f9bad';x.font='11px ui-monospace';x.fillText(hi.toFixed(3),2,12);x.fillText(lo.toFixed(3),2,h-4)}
async function refresh(){try{const r=await fetch('/api/status',{cache:'no-store'}),d=await r.json(),p=d.progress,stage=d.status.stage||'unknown';$('stage').innerHTML=`<span class="${d.healthy?'good':'bad'}">${d.healthy?'● healthy':'● attention'}</span> · ${stage.replaceAll('_',' ')}`;$('freshness').textContent='Updated '+new Date(d.generated_at_unix*1000).toLocaleTimeString();$('progress').textContent=`${pct(p.fraction)} · epoch ${p.epoch}/${p.epochs}`;$('progressBar').style.width=pct(p.fraction);$('eta').textContent=`${num(p.completed_microbatches)} / ${num(p.total_microbatches)} microbatches · ${duration(p.eta_seconds)}`;
const g=d.gpu;$('gpu').textContent=g.utilization_percent==null?'—':g.utilization_percent+'%';$('gpuSub').textContent=g.memory_used_mib==null?'nvidia-smi unavailable':`${(g.memory_used_mib/1024).toFixed(1)} / ${(g.memory_total_mib/1024).toFixed(1)} GiB · ${g.temperature_c}°C`;$('disk').textContent=gib(d.disk.free_bytes);$('diskSub').textContent=pct(d.disk.used_fraction)+' used';chart(d.recent_losses);
$('validations').innerHTML=d.validation_history.length?d.validation_history.map(v=>metric('Epoch '+v.epoch,v.loss)).join(''):'Not yet available';$('checkpoints').innerHTML=d.checkpoints.length?`<table><tr><th>Name</th><th>Update</th><th>Best val</th></tr>${d.checkpoints.slice(-7).reverse().map(c=>`<tr><td>${c.name}</td><td>${num(c.global_updates)}</td><td>${c.best_validation_loss==null?'—':c.best_validation_loss.toFixed(4)}</td></tr>`).join('')}</table>`:'None yet';
const entries=Object.entries(d.evaluations);$('evaluation').innerHTML=entries.length?entries.map(([name,m])=>{const ci=m.autoregressive_exact_action_cluster_bootstrap,ciText=ci?.available?`${pct(ci.lower)} – ${pct(ci.upper)} (${num(ci.clusters)} replays)`:'—';return `<div style="margin-bottom:14px"><strong>${name}</strong>${metric('Exact action · autoregressive',m.autoregressive_exact_action_accuracy,true)}${metric('Replay-cluster 95% CI',ciText)}${metric('Changed-action exact · autoregressive',m.autoregressive_changed_exact_action_accuracy,true)}${metric('Exact action · teacher forced',m.constrained_exact_action_accuracy,true)}${metric('Changed component',m.changed_component_accuracy,true)}${metric('Change precision',m.change_precision,true)}${metric('Change recall',m.change_recall,true)}${metric('Repeat previous',m.previous_mask_exact_action_accuracy,true)}</div>`}).join(''):'Available after final evaluation.';
$('errorCard').classList.toggle('hidden',!d.errors.length);$('errors').textContent=d.errors.join('\n');}catch(e){$('stage').innerHTML='<span class="bad">● disconnected</span>';console.error(e)}}
refresh();setInterval(refresh,10000);addEventListener('resize',refresh);
</script></body></html>"""


class DashboardHandler(BaseHTTPRequestHandler):
    workspace: Path
    training_root: Path
    training_log: Path

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/api/status":
            self.respond(
                json.dumps(
                    build_snapshot(
                        self.workspace,
                        training_root=self.training_root,
                        log_path=self.training_log,
                    )
                ).encode(),
                "application/json",
            )
        elif self.path == "/healthz":
            self.respond(b"ok\n", "text/plain")
        elif self.path in {"/", "/index.html"}:
            self.respond(HTML.encode(), "text/html; charset=utf-8")
        else:
            self.send_error(404)

    def respond(self, body: bytes, content_type: str) -> None:
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        return


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--training-root", type=Path)
    parser.add_argument("--training-log", type=Path)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    if not args.workspace.exists():
        parser.error(f"workspace does not exist: {args.workspace}")
    DashboardHandler.workspace = args.workspace.resolve()
    DashboardHandler.training_root = (
        args.training_root or args.workspace / "training-v1"
    ).resolve()
    DashboardHandler.training_log = (
        args.training_log
        or args.workspace.parent.parent / "logs" / "expert-training-v1.log"
    ).resolve()
    server = ThreadingHTTPServer((args.host, args.port), DashboardHandler)
    print(f"Paintbot RL dashboard: http://{args.host}:{args.port}", flush=True)
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
