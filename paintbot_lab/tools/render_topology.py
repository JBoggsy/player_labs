#!/usr/bin/env python3
"""Render the Layer 2 topology PROCESS from an agent trace as interactive HTML.

Pipeline:
  1. Read a stencil trace JSONL (local self_play `players/slot-XX.trace.jsonl`
     or a downloaded artifact member) and extract the `navigation_map` event —
     which carries the agent's exact clearance field (`clearance_packed`), its
     final rooms/chokes/cover/gates, and the topology knobs it ran with.
  2. Decode the clearance field and re-run the EXACT topology code via
     tools/topology_debug.nim (compiled on demand against stencil_nim) with a
     process journal: pre-merge watershed labels, seeds, saddle contacts, and
     every merge decision.
  3. Cross-check the harness's finals against the agent-traced finals (drift
     guard — refuses to render silently on mismatch; see --allow-drift).
  4. Emit a self-contained HTML viewer: a clearance-level scrubber that
     replays the watershed flood exactly (a pixel is labeled at its own
     clearance level), merged/raw/component views, choke gates, cover roses,
     and the defense-gate scoring table.

Usage:
  uv run python tools/render_topology.py TRACE.jsonl [-o topology.html]
      [--allow-drift] [--open]
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import subprocess
import sys
import tempfile
import webbrowser
import zlib
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
STENCIL_DIR = TOOLS_DIR.parent / "paintbot" / "stencil_nim"
HARNESS_SRC = TOOLS_DIR / "topology_debug.nim"
HARNESS_BIN = TOOLS_DIR / "bin" / "topology_debug"
HARNESS_DEPS = [
    HARNESS_SRC,
    STENCIL_DIR / "worldmap.nim",
    STENCIL_DIR / "config.nim",
    STENCIL_DIR / "types.nim",
]


def load_navigation_map(path: Path) -> dict:
    for line in path.read_text().splitlines():
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if row.get("event") == "navigation_map":
            return row["data"]
    raise SystemExit(f"no navigation_map event found in {path}")


def decode_clearance(packed: dict) -> bytes:
    if packed["encoding"] != "clearance-delta-zlib-b64":
        raise SystemExit(f"unknown clearance encoding {packed['encoding']!r}")
    deltas = zlib.decompress(base64.b64decode(packed["data"]))
    if len(deltas) != packed["width"] * packed["height"]:
        raise SystemExit("clearance_packed length mismatch")
    out = bytearray(len(deltas))
    value = 0
    for index, delta in enumerate(deltas):
        value = (value + delta) & 0xFF
        out[index] = value
    return bytes(out)


def ensure_harness() -> Path:
    if HARNESS_BIN.exists():
        built = HARNESS_BIN.stat().st_mtime
        if all(dep.stat().st_mtime < built for dep in HARNESS_DEPS):
            return HARNESS_BIN
    HARNESS_BIN.parent.mkdir(parents=True, exist_ok=True)
    print("render_topology: compiling topology_debug harness...", file=sys.stderr)
    subprocess.run(
        [
            "nim", "c", "-d:release", "--hints:off",
            f"--path:{STENCIL_DIR}",
            f"-o:{HARNESS_BIN}",
            str(HARNESS_SRC),
        ],
        check=True,
        cwd=TOOLS_DIR,
    )
    return HARNESS_BIN


def run_harness(nav: dict, clearance: bytes) -> dict:
    teams_meta = []
    for index, team in enumerate(nav["teams"]):
        zone = team.get("endzone")
        if zone:
            teams_meta.append(
                {
                    "team": index,
                    "shape": zone["shape"],
                    "x0": zone["box"][0],
                    "y0": zone["box"][1],
                    "x1": zone["box"][2],
                    "y1": zone["box"][3],
                }
            )
    meta = {
        "width": nav["map"][0],
        "height": nav["map"][1],
        "teams": len(nav["teams"]),
        "team": 0,
        "endzones": teams_meta,
    }
    env = os.environ.copy()
    # Reproduce the agent's knobs exactly (they ride in the trace payload).
    env["STENCIL_COVER_RAYS"] = str(nav["cover_rays"])
    env["STENCIL_COVER_RAY_PX"] = str(nav["cover_ray_px"])
    env["STENCIL_TOPOLOGY_MERGE_DEPTH_PX"] = str(nav["merge_depth_px"])
    env["STENCIL_TOPOLOGY_MERGE_RATIO"] = str(nav["merge_ratio"])
    env["STENCIL_GATE_DETOUR_PX"] = str(nav["gate_detour_px"])
    env["STENCIL_GATE_SEPARATION_PX"] = str(nav["gate_separation_px"])
    harness = ensure_harness()
    with tempfile.TemporaryDirectory() as tmp:
        meta_path = Path(tmp) / "meta.json"
        clearance_path = Path(tmp) / "clearance.bin"
        out_path = Path(tmp) / "process.json"
        meta_path.write_text(json.dumps(meta))
        clearance_path.write_bytes(clearance)
        subprocess.run(
            [str(harness), str(meta_path), str(clearance_path), str(out_path)],
            check=True,
            env=env,
        )
        return json.loads(out_path.read_text())


def cross_check(nav: dict, process: dict, allow_drift: bool) -> list[str]:
    """The drift guard: the harness re-ran the agent's code on the agent's
    clearance — finals must match the agent's traced finals bit-for-bit."""
    problems: list[str] = []

    def agent_cover_dirs() -> list[int]:
        cells: list[int] = []
        for row in nav["cover_dirs_rows"]:
            cells.extend(int(row[i : i + 4], 16) for i in range(0, len(row), 4))
        return cells

    if nav["components_n"] != process["components_n"]:
        problems.append(
            f"components_n: agent {nav['components_n']} != harness {process['components_n']}"
        )
    for kind in ("rooms", "chokes"):
        agent_items = nav[kind]
        harness_items = process[kind]
        if len(agent_items) != len(harness_items):
            problems.append(
                f"{kind}: agent {len(agent_items)} != harness {len(harness_items)}"
            )
        else:
            for index, (a, b) in enumerate(zip(agent_items, harness_items)):
                if a != b:
                    problems.append(f"{kind}[{index}]: agent {a} != harness {b}")
                    break
    if agent_cover_dirs() != process["cover_dirs"]:
        problems.append("cover_dirs: agent grid != harness grid")
    for index, team in enumerate(nav["teams"]):
        gate = process["anchors"][index]["gate"]
        if team["defense_gate"] != gate:
            problems.append(
                f"defense_gate[{index}]: agent {team['defense_gate']} != harness {gate}"
            )
    if problems:
        report = "\n  ".join(problems)
        message = f"agent-vs-harness drift detected:\n  {report}"
        if not allow_drift:
            raise SystemExit(
                f"render_topology: {message}\n"
                "(same code should give identical results on the same clearance; "
                "a mismatch means version skew between the trace and this checkout. "
                "Pass --allow-drift to render anyway.)"
            )
        print(f"render_topology: WARNING: {message}", file=sys.stderr)
    return problems


def rle_to_u16_bytes(rle: list[list[int]]) -> bytes:
    out = bytearray()
    for value, run in rle:
        chunk = int(value).to_bytes(2, "little") * run
        out.extend(chunk)
    return bytes(out)


def pack_b64(raw: bytes) -> str:
    return base64.b64encode(zlib.compress(raw, 6)).decode()


def render_html(nav: dict, process: dict, drift: list[str], clearance: bytes) -> str:
    width, height = nav["map"]
    viewer = {
        "width": width,
        "height": height,
        "grid": nav["grid"],
        "cell_size": nav["cell_size"],
        "cover_rays": process["cover_rays"],
        "cover_ray_px": process["cover_ray_px"],
        "merge_depth_px": process["merge_depth_px"],
        "merge_ratio": process["merge_ratio"],
        "gate_detour_px": process["gate_detour_px"],
        "components_n": process["components_n"],
        "rooms": process["rooms"],
        "chokes": process["chokes"],
        "seeds": process["seeds"],
        "contacts": process["contacts"],
        "merges": process["merges"],
        "cover_dirs": process["cover_dirs"],
        "anchors": process["anchors"],
        "teams": [
            {
                "team": team["team"],
                "home_center": team["home_center"],
                "defense_gate": team["defense_gate"],
                "endzone": team.get("endzone"),
            }
            for team in nav["teams"]
        ],
        "timings_ms": {
            "component": process["component_ms"],
            "topology": process["topology_ms"],
            "cover": process["cover_ms"],
        },
        "drift": drift,
    }
    payload = json.dumps(viewer, separators=(",", ":")).replace("</", "<\\/")
    blobs = {
        "clearance": pack_b64(clearance),
        "raw": pack_b64(rle_to_u16_bytes(process["raw_labels_rle"])),
        "final": pack_b64(rle_to_u16_bytes(process["final_labels_rle"])),
        "component": pack_b64(rle_to_u16_bytes(process["component_labels_rle"])),
    }
    blob_json = json.dumps(blobs)
    return (
        HTML_TEMPLATE.replace("__PAYLOAD__", payload).replace("__BLOBS__", blob_json)
    )


HTML_TEMPLATE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Stencil topology process</title>
<style>
:root { color-scheme:dark; font-family:system-ui,sans-serif; background:#11151a; color:#e7edf3 }
body { margin:0; display:grid; grid-template-columns:300px minmax(0,1fr); min-height:100vh }
aside { padding:20px; background:#192129; border-right:1px solid #33404b; overflow:auto }
main { padding:20px; overflow:auto }
h1 { font-size:19px; margin:0 0 12px } h2 { font-size:13px; margin:18px 0 6px; color:#9fb2c2 }
label { display:block; margin:8px 0; font-size:13px }
canvas { background:#0b0e11; box-shadow:0 2px 16px #0008; image-rendering:pixelated }
#tip { margin-top:12px; min-height:6em; font:12px ui-monospace,monospace; white-space:pre-wrap }
#level { width:100% }
button { background:#26313c; color:#e7edf3; border:1px solid #33404b; border-radius:4px; padding:4px 10px; cursor:pointer }
table { border-collapse:collapse; font:12px ui-monospace,monospace; margin-top:8px }
td,th { padding:2px 8px; text-align:right; border-bottom:1px solid #26313c }
th { color:#9fb2c2 } tr.qualified td { color:#9be29b } tr.chosen td { color:#ffd166; font-weight:600 }
tr.merged td { color:#8aa0b4 } tr.kept td { color:#e7b3b3 }
.warn { background:#4a2626; padding:8px 10px; border-radius:4px; font-size:12px; margin-bottom:10px }
.summary { font:12px ui-monospace,monospace; color:#9fb2c2; line-height:1.6 }
</style></head><body><aside><h1>Stencil topology process</h1>
<div id="drift"></div>
<div class="summary" id="summary"></div>
<h2>Watershed flood</h2>
<label>level <span id="levelValue"></span><input id="level" type="range"></label>
<button id="play">play flood</button>
<h2>View</h2>
<label><input type="radio" name="view" value="raw" checked> raw watershed rooms</label>
<label><input type="radio" name="view" value="final"> merged rooms (final)</label>
<label><input type="radio" name="view" value="component"> components</label>
<label><input type="radio" name="view" value="clearance"> clearance heatmap</label>
<h2>Overlays</h2>
<label><input id="seeds" type="checkbox" checked> seeds (room maxima)</label>
<label><input id="contactsBox" type="checkbox"> saddle contacts (all)</label>
<label><input id="chokesBox" type="checkbox" checked> chokes (final gates)</label>
<label><input id="peaks" type="checkbox" checked> room peaks + ids</label>
<label><input id="coverBox" type="checkbox"> cover roses (per cell)</label>
<label><input id="gates" type="checkbox" checked> defense gates + homes</label>
<div id="tip"></div></aside>
<main><canvas id="map"></canvas>
<h2>Defense-gate scoring</h2><div id="anchorTables"></div>
<h2>Merge log (flood order)</h2><div id="mergeTable"></div>
</main><script>
const data=__PAYLOAD__;
const blobs=__BLOBS__;
async function inflate(b64){
  const raw=Uint8Array.from(atob(b64),c=>c.charCodeAt(0));
  const stream=new Blob([raw]).stream().pipeThrough(new DecompressionStream('deflate'));
  return new Uint8Array(await new Response(stream).arrayBuffer());
}
(async()=>{
const W=data.width,H=data.height;
const clearance=await inflate(blobs.clearance);
const raw=new Uint16Array((await inflate(blobs.raw)).buffer);
const fin=new Uint16Array((await inflate(blobs.final)).buffer);
const comp=new Uint16Array((await inflate(blobs.component)).buffer);
let maxClear=0; for(let i=0;i<clearance.length;i++) if(clearance[i]>maxClear) maxClear=clearance[i];
const canvas=document.querySelector('#map'),ctx=canvas.getContext('2d');
const scale=Math.min(4,Math.max(0.28,Math.min((window.innerWidth-360)/W,(window.innerHeight-80)/H)));
canvas.width=W; canvas.height=H;
canvas.style.width=Math.round(W*scale)+'px'; canvas.style.height=Math.round(H*scale)+'px';
const img=ctx.createImageData(W,H); const px=new Uint32Array(img.data.buffer);
function labelColor(label,alpha){ // golden-angle hue spread, stable per label
  const h=(label*137.508)%360, s=62, l=52;
  const a=s*Math.min(l,100-l)/100;
  const f=n=>{const k=(n+h/30)%12; return l/100-a/100*Math.max(-1,Math.min(k-3,9-k,1));};
  return (alpha<<24)|(Math.round(f(4)*255)<<16)|(Math.round(f(8)*255)<<8)|Math.round(f(0)*255);
}
const WALL=0xff11100e, UNFLOODED=0xff2a3138, UNSTANDABLE=0xff1c2126;
const rawLut=[0],finLut=[0],compLut=[0];
for(let i=1;i<=data.seeds.length;i++) rawLut[i]=labelColor(i,255);
for(let i=1;i<=data.rooms.length;i++) finLut[i]=labelColor(i,255);
for(let i=1;i<=data.components_n;i++) compLut[i]=labelColor(i*7+3,255);
const levelInput=document.querySelector('#level');
levelInput.min=7; levelInput.max=maxClear; levelInput.value=7;
function view(){ return document.querySelector('input[name=view]:checked').value; }
function repaint(){
  const L=+levelInput.value; document.querySelector('#levelValue').textContent=
    view()==='raw'?`${L} px (flooded: clearance >= ${L})`:'(final state)';
  const mode=view();
  for(let i=0;i<W*H;i++){
    const c=clearance[i];
    if(c===0){ px[i]=WALL; continue; }
    if(c<=6){ px[i]=UNSTANDABLE; continue; }   // walkable pixel, not standable
    if(mode==='raw'){ px[i]=c>=L?rawLut[raw[i]]:UNFLOODED; }
    else if(mode==='final'){ px[i]=finLut[fin[i]]; }
    else if(mode==='component'){ px[i]=compLut[comp[i]]; }
    else { const v=Math.round(40+215*Math.min(1,c/Math.max(1,maxClear))); px[i]=(255<<24)|(v<<16)|(v<<8)|v; }
  }
  ctx.putImageData(img,0,0); overlays();
}
function dot(p,color,r){ ctx.fillStyle=color; ctx.beginPath(); ctx.arc(p[0],p[1],r,0,7); ctx.fill(); }
function overlays(){
  const L=+levelInput.value, mode=view();
  ctx.save(); ctx.lineWidth=Math.max(1,1.2/scale);
  (data.teams||[]).forEach(t=>{
    if(!t.endzone) return; const b=t.endzone.box;
    ctx.strokeStyle='#9fb2c288'; ctx.strokeRect(b[0],b[1],b[2]-b[0],b[3]-b[1]);
  });
  if(document.querySelector('#seeds').checked)
    data.seeds.forEach(s=>{ if(mode!=='raw'||s.clearance>=L) dot(s.pos,'#ffffffcc',Math.max(2,2/scale)); });
  if(document.querySelector('#contactsBox').checked)
    data.contacts.forEach(c=>{ if(mode!=='raw'||c.clearance>=L) dot(c.pos,'#f06595aa',Math.max(1.5,1.5/scale)); });
  if(document.querySelector('#chokesBox').checked)
    data.chokes.forEach(c=>{ if(mode==='raw'&&c.clearance<L) return;
      ctx.strokeStyle='#ffd166'; const r=c.clearance;
      ctx.strokeRect(c.pos[0]-r,c.pos[1]-r,2*r,2*r); dot(c.pos,'#ffd166',Math.max(2,2/scale)); });
  if(document.querySelector('#peaks').checked&&mode==='final')
    data.rooms.forEach((r,i)=>{ dot(r.peak,'#ffffff88',Math.max(2,2/scale));
      ctx.fillStyle='#e7edf3'; ctx.font=`${Math.max(10,12/scale)}px ui-monospace`;
      ctx.fillText(String(i+1),r.peak[0]+3,r.peak[1]-3); });
  if(document.querySelector('#coverBox').checked){
    // Per-cell wedge rose: filled sectors point AT the blocking wall (the
    // directions this cell is covered FROM); the open remainder is the
    // cell's vulnerability fan. Wedges stay inside the cell so they can't
    // be misread as wall decorations (long undirected spokes were).
    const cell=data.cell_size,[gw,gh]=data.grid,n=data.cover_rays;
    const r=cell*0.46, half=Math.PI/n;
    ctx.fillStyle='#49c6e5b8';
    for(let gy=0;gy<gh;gy++) for(let gx=0;gx<gw;gx++){
      const mask=data.cover_dirs[gy*gw+gx]; if(!mask) continue;
      const cx=gx*cell+cell/2, cy=gy*cell+cell/2;
      for(let k=0;k<n;k++){ if(!(mask&(1<<k))) continue;
        const a=k*2*Math.PI/n;
        ctx.beginPath(); ctx.moveTo(cx,cy);
        ctx.arc(cx,cy,r,a-half,a+half); ctx.closePath(); ctx.fill(); }
      ctx.fillStyle='#e7edf3'; ctx.fillRect(cx-0.6,cy-0.6,1.2,1.2);
      ctx.fillStyle='#49c6e5b8';
    }
  }
  if(document.querySelector('#gates').checked)
    (data.anchors||[]).forEach((a,i)=>{ dot(a.home,'#69db7c',Math.max(3,3/scale));
      dot(a.gate,'#ff922b',Math.max(3.5,3.5/scale));
      ctx.fillStyle='#ff922b'; ctx.font=`${Math.max(10,12/scale)}px ui-monospace`;
      ctx.fillText('G'+i,a.gate[0]+4,a.gate[1]+4); });
  ctx.restore();
}
let playing=null;
document.querySelector('#play').onclick=()=>{
  if(playing){ clearInterval(playing); playing=null; document.querySelector('#play').textContent='play flood'; return; }
  document.querySelector('input[name=view][value=raw]').checked=true;
  levelInput.value=maxClear;
  document.querySelector('#play').textContent='stop';
  playing=setInterval(()=>{ if(+levelInput.value<=7){ clearInterval(playing); playing=null;
      document.querySelector('#play').textContent='play flood'; return; }
    levelInput.value=+levelInput.value-1; repaint(); },120);
};
levelInput.oninput=repaint;
document.querySelectorAll('input').forEach(el=>{ if(el.id!=='level') el.onchange=repaint; });
canvas.onmousemove=e=>{
  const rect=canvas.getBoundingClientRect();
  const x=Math.floor((e.clientX-rect.left)/scale), y=Math.floor((e.clientY-rect.top)/scale);
  if(x<0||x>=W||y<0||y>=H) return;
  const i=y*W+x, cell=data.cell_size;
  const gx=Math.min(Math.floor(x/cell),data.grid[0]-1), gy=Math.min(Math.floor(y/cell),data.grid[1]-1);
  const mask=data.cover_dirs[gy*data.grid[0]+gx]||0;
  document.querySelector('#tip').textContent=
    `pixel (${x}, ${y})\nclearance ${clearance[i]} px  standable ${clearance[i]>6}\n`+
    `raw room ${raw[i]||'-'}   final room ${fin[i]||'-'}\ncomponent ${comp[i]||'-'}\n`+
    `cell (${gx}, ${gy}) cover mask ${mask.toString(2).padStart(data.cover_rays,'0')}`;
};
// panels
const drift=document.querySelector('#drift');
if(data.drift.length) drift.innerHTML=`<div class="warn">DRIFT: ${data.drift.join('<br>')}</div>`;
document.querySelector('#summary').innerHTML=
  `${W}x${H} px - ${data.components_n} components, ${data.rooms.length} rooms, `+
  `${data.chokes.length} chokes, ${data.seeds.length} raw seeds<br>`+
  `merge depth ${data.merge_depth_px} px, ratio ${data.merge_ratio}; cover ${data.cover_rays} rays x ${data.cover_ray_px} px<br>`+
  `harness ms: component ${data.timings_ms.component.toFixed(1)}, topology ${data.timings_ms.topology.toFixed(1)}, cover ${data.timings_ms.cover.toFixed(1)}`;
const anchorDiv=document.querySelector('#anchorTables');
(data.anchors||[]).forEach(anchor=>{
  const sorted=[...anchor.chokes].sort((a,b)=>
    (b.qualified-a.qualified)||((a.qualified?a.from_home:a.detour??1e9)-(b.qualified?b.from_home:b.detour??1e9)));
  const rows=sorted.map((c,i)=>{
    const chosen=!anchor.fallback_used&&c.pos[0]===anchor.gate[0]&&c.pos[1]===anchor.gate[1];
    return `<tr class="${chosen?'chosen':c.qualified?'qualified':''}"><td>(${c.pos[0]}, ${c.pos[1]})</td>`+
      `<td>${c.from_home==null?'unreachable':c.from_home.toFixed(0)}</td>`+
      `<td>${c.to_enemy==null?'unreachable':c.to_enemy.toFixed(0)}</td>`+
      `<td>${c.detour==null?'-':c.detour.toFixed(0)}</td><td>${c.qualified?'yes':''}</td>`+
      `<td>${chosen?'&larr; gate':''}</td></tr>`; }).join('');
  anchorDiv.innerHTML+=`<p class="summary">team ${anchor.team}: home (${anchor.home}) &rarr; enemy (${anchor.enemy_home}), `+
    `direct ${anchor.direct==null?'unreachable':anchor.direct.toFixed(0)} px`+
    `${anchor.fallback_used?' - NO qualifying gate, fell back to home-room peak':''}</p>`+
    `<table><tr><th>choke</th><th>from home</th><th>to enemy</th><th>detour</th><th>qualified</th><th></th></tr>${rows}</table>`;
});
document.querySelector('#mergeTable').innerHTML='<table><tr><th>#</th><th>pair</th><th>saddle</th><th>depth</th><th>ratio</th><th>verdict</th></tr>'+
  data.merges.map((m,i)=>`<tr class="${m.merged?'merged':'kept'}"><td>${i+1}</td><td>${m.pair[0]}+${m.pair[1]}</td>`+
    `<td>${m.saddle}</td><td>${m.depth}</td><td>${m.ratio.toFixed(2)}</td><td>${m.merged?'merged':'kept as gate'}</td></tr>`).join('')+'</table>';
repaint();
})();
</script></body></html>
"""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("trace", type=Path, help="stencil trace JSONL with a navigation_map event")
    parser.add_argument("-o", "--output", type=Path, default=None)
    parser.add_argument("--allow-drift", action="store_true",
                        help="render despite agent-vs-harness mismatches (version skew)")
    parser.add_argument("--open", action="store_true", help="open the result in a browser")
    args = parser.parse_args()

    nav = load_navigation_map(args.trace)
    if nav.get("schema_version", 0) < 3 or "clearance_packed" not in nav:
        raise SystemExit(
            "trace predates navigation_map schema v3 (no clearance_packed); "
            "re-run with a v62+ stencil build"
        )
    clearance = decode_clearance(nav["clearance_packed"])
    process = run_harness(nav, clearance)
    drift = cross_check(nav, process, args.allow_drift)
    output = args.output or args.trace.with_suffix(".topology.html")
    output.write_text(render_html(nav, process, drift, clearance))
    print(f"render_topology: wrote {output}"
          f" ({len(process['rooms'])} rooms, {len(process['chokes'])} chokes)")
    if args.open:
        webbrowser.open(output.resolve().as_uri())


if __name__ == "__main__":
    main()
