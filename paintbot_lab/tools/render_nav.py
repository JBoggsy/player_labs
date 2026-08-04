#!/usr/bin/env python3
"""Render stencil's opt-in navigation trace as a standalone HTML canvas viewer."""

from __future__ import annotations

import argparse
import json
import zipfile
from pathlib import Path


def trace_lines(path: Path) -> list[str]:
    if path.suffix != ".zip":
        return path.read_text().splitlines()
    with zipfile.ZipFile(path) as archive:
        candidates = [name for name in archive.namelist() if name.endswith(".jsonl")]
        if not candidates:
            raise ValueError(f"{path} contains no JSONL trace")
        preferred = "telemetry.jsonl" if "telemetry.jsonl" in candidates else candidates[0]
        return archive.read(preferred).decode().splitlines()


def load_navigation(path: Path) -> dict:
    navigation_map = None
    flows: list[dict] = []
    for line in trace_lines(path):
        row = json.loads(line)
        if row.get("event") == "navigation_map":
            navigation_map = row["data"]
            flows = []
        elif row.get("event") == "navigation_flow" and navigation_map is not None:
            flows.append(row["data"])
    if navigation_map is None:
        raise ValueError(
            "trace has no navigation_map event; run with STENCIL_TRACE_NAVIGATION=1 "
            "or self_play.py --visualize-nav"
        )
    navigation_map["flows"] = flows
    return navigation_map


def render_html(data: dict) -> str:
    payload = json.dumps(data, separators=(",", ":")).replace("</", "<\\/")
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Stencil navigation knowledge</title>
<style>
:root {{ color-scheme:dark; font-family:system-ui,sans-serif; background:#11151a; color:#e7edf3 }}
body {{ margin:0; display:grid; grid-template-columns:280px minmax(0,1fr); min-height:100vh }}
aside {{ padding:20px; background:#192129; border-right:1px solid #33404b }}
main {{ padding:20px; overflow:auto }} h1 {{ font-size:19px; margin:0 0 16px }}
label {{ display:block; margin:10px 0 }} select {{ width:100%; margin-top:5px }}
canvas {{ background:#0b0e11; box-shadow:0 2px 16px #0008; image-rendering:pixelated }}
#tip {{ margin-top:14px; min-height:5em; font:12px ui-monospace,monospace; white-space:pre-wrap }}
.legend {{ font-size:12px; line-height:1.7; margin-top:18px }}
.swatch {{ display:inline-block; width:10px; height:10px; margin-right:6px }}
</style></head><body><aside><h1>Stencil navigation knowledge</h1>
<div id="summary"></div>
<label>Flow field<select id="flow"></select></label>
<label><input id="distance" type="checkbox" checked> route distance heatmap</label>
<label><input id="cover" type="checkbox" checked> cover cells</label>
<label><input id="arrows" type="checkbox" checked> next-hop arrows</label>
<label><input id="anchors" type="checkbox" checked> tactical anchors</label>
<div class="legend"><span class="swatch" style="background:#d9d4c7"></span>walkable<br>
<span class="swatch" style="background:#49c6e5"></span>cover<br>
Distance: dark near goal → orange far away</div><div id="tip"></div></aside>
<main><canvas id="map"></canvas></main><script>
const data={payload}; const [gw,gh]=data.grid, [mw,mh]=data.map, cell=data.cell_size;
const canvas=document.querySelector('#map'), ctx=canvas.getContext('2d');
const scale=Math.min(8,1200/gw,850/gh);
canvas.width=Math.ceil(gw*scale); canvas.height=Math.ceil(gh*scale);
const flowSelect=document.querySelector('#flow');
data.flows.forEach((flow,i)=>{{
  const option=document.createElement('option'); option.value=i;
  option.textContent=`${{i+1}}: goal (${{flow.goal[0]}}, ${{flow.goal[1]}})`;
  flowSelect.append(option);
}});
if(!data.flows.length){{
  const option=document.createElement('option'); option.textContent='none cached';
  flowSelect.append(option);
}}
document.querySelector('#summary').textContent=
  `${{mw}}×${{mh}} px · ${{gw}}×${{gh}} cells · ${{data.flows.length}} cached goals`;
const neighbors=[[-1,0],[1,0],[0,-1],[0,1],[-1,-1],[-1,1],[1,-1],[1,1]];
function checked(id){{ return document.querySelector(id).checked }}
function draw(){{
  const flow=data.flows[Number(flowSelect.value)]||null;
  ctx.clearRect(0,0,canvas.width,canvas.height);
  let maxDistance=0;
  if(flow) for(const row of flow.distance_cells) for(const d of row)
    if(d!==null) maxDistance=Math.max(maxDistance,d);
  for(let y=0;y<gh;y++) for(let x=0;x<gw;x++){{
    if(data.walkable_rows[y][x]==='0') continue;
    let color='#d9d4c7'; const d=flow?.distance_cells[y][x];
    if(checked('#distance')&&d!==null&&d!==undefined){{
      const t=d/maxDistance; color=`hsl(${{28-20*t}} 75% ${{24+28*t}}%)`;
    }}
    ctx.fillStyle=color;
    ctx.fillRect(x*scale,y*scale,Math.ceil(scale),Math.ceil(scale));
    if(checked('#cover')&&data.cover_rows[y][x]==='1'){{
      ctx.fillStyle='#49c6e5aa';
      ctx.fillRect(x*scale,y*scale,Math.ceil(scale),Math.ceil(scale));
    }}
  }}
  if(flow&&checked('#arrows')&&scale>=2){{
    ctx.strokeStyle='#f6f7f8aa'; ctx.lineWidth=Math.max(.5,scale*.12);
    const stride=scale<4?2:1;
    for(let y=0;y<gh;y+=stride) for(let x=0;x<gw;x+=stride){{
      const code=Number(flow.hop_rows[y][x]); if(!code) continue;
      const [dx,dy]=neighbors[code-1], cx=(x+.5)*scale, cy=(y+.5)*scale;
      ctx.beginPath(); ctx.moveTo(cx,cy);
      ctx.lineTo(cx+dx*scale*.38,cy+dy*scale*.38); ctx.stroke();
    }}
  }}
  if(checked('#anchors')) drawAnchors();
}}
function dot(point,color,label){{
  const x=point[0]/cell*scale,y=point[1]/cell*scale;
  ctx.fillStyle=color; ctx.beginPath();
  ctx.arc(x,y,Math.max(3,scale*.65),0,Math.PI*2); ctx.fill();
  ctx.fillStyle='#fff'; ctx.font='11px system-ui'; ctx.fillText(label,x+6,y-5);
}}
function drawAnchors(){{
  dot(data.center,'#fff','center');
  for(const team of data.teams){{
    const color=team.team==='yellow'?'#ffd43b':team.team, zone=team.endzone;
    if(zone){{
      ctx.strokeStyle=color; ctx.lineWidth=2;
      ctx.strokeRect(zone.box[0]/cell*scale,zone.box[1]/cell*scale,
        (zone.box[2]-zone.box[0])/cell*scale,(zone.box[3]-zone.box[1])/cell*scale);
    }}
    dot(team.capture,color,team.team+' capture');
    dot(team.choke,'#d980fa',team.team+' choke');
    dot(team.rally,'#69db7c',team.team+' rally');
    if(team.pedestal) dot(team.pedestal,'#fff3bf',team.team+' heart');
  }}
}}
for(const element of document.querySelectorAll('input,select'))
  element.addEventListener('change',draw);
canvas.addEventListener('mousemove',event=>{{
  const rect=canvas.getBoundingClientRect();
  const x=Math.min(gw-1,Math.floor((event.clientX-rect.left)*canvas.width/rect.width/scale));
  const y=Math.min(gh-1,Math.floor((event.clientY-rect.top)*canvas.height/rect.height/scale));
  const flow=data.flows[Number(flowSelect.value)], d=flow?.distance_cells[y][x];
  const hop=flow?Number(flow.hop_rows[y][x]):0;
  document.querySelector('#tip').textContent=
    `cell (${{x}}, ${{y}}) · world (${{x*cell+cell/2}}, ${{y*cell+cell/2}})\n`+
    `walkable=${{data.walkable_rows[y][x]==='1'}} cover=${{data.cover_rows[y][x]==='1'}}\n`+
    `distance=${{d===null||d===undefined?'unreachable':(d*cell).toFixed(1)+' px'}} `+
    `next-hop=${{hop?neighbors[hop-1]:'none'}}`;
}});
draw();
</script></body></html>"""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("trace", type=Path, help="trace JSONL or player artifact ZIP")
    parser.add_argument("--output", "-o", type=Path, help="output HTML path")
    args = parser.parse_args()
    output = args.output or args.trace.with_suffix(".nav.html")
    output.write_text(render_html(load_navigation(args.trace)))
    print(output.resolve())


if __name__ == "__main__":
    main()
