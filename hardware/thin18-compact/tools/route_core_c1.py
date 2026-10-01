#!/usr/bin/env python3
"""Conservative geometry-guided J601 routing; native DRC is the acceptance gate."""
from pathlib import Path
import argparse, heapq, json, math, sys, uuid

import numpy as np
from scipy.ndimage import distance_transform_edt
import shapely
from shapely.geometry import Polygon, Point, LineString, box

ap = argparse.ArgumentParser()
ap.add_argument("pcb", type=Path)
ap.add_argument("geometry", type=Path)
ap.add_argument("report", type=Path)
a = ap.parse_args()
g = json.loads(a.geometry.read_text())
import hashlib
if hashlib.sha256(a.pcb.read_bytes()).hexdigest() != g.get("pcb_sha256"):
    raise SystemExit("Geometry does not match the current PCB; export a fresh snapshot.")
layers = g["layers"]
native_layers = ["F.Cu", "In1.Cu", "In2.Cu", "B.Cu"]
STEP = 0.025
xmin, ymin, xmax, ymax = 52., 45., 84., 67.55
xs = np.arange(xmin, xmax + STEP/2, STEP)
ys = np.arange(ymin, ymax + STEP/2, STEP)
xx, yy = np.meshgrid(xs, ys)
NY, NX = xx.shape
window = box(xmin-1, ymin-1, xmax+1, ymax+1)
items = []
for row in g["items"]:
    shapes = [Polygon(p) for p in row["polygons"] if len(p) >= 3]
    geom = shapely.union_all(shapes)
    if not geom.is_empty:
        items.append(dict(row, geom=geom, li=layers.index(row["layer"])))
# Reserve an escape corridor for every unfinished signal before routing any net.
for r in tuple(items):
    if r["type"] == "pad" and r["ref"] == "J601" and r["net"].startswith("EPD_D"):
        x,y=r["position"]
        items.append({"type":"reservation","net":r["net"],"li":r["li"],
            "geom":LineString([(x,y),(x,62.0)]).buffer(0.075)})
holes = [Point(h["position"]).buffer(max(h["size"])/2 + 0.125 + 0.25 + 0.01)
    for h in g["holes"]]
hole_obstacle = shapely.union_all(holes)
routes, segments, vias = [], [], []
def idx(p):
    return (int(round((p[1]-ymin)/STEP)), int(round((p[0]-xmin)/STEP)))
def point(y,x): return (round(float(xs[x]),6), round(float(ys[y]),6))
def union(rows): return shapely.union_all([r["geom"] for r in rows])
def mask(geom): return shapely.intersects_xy(geom, xx, yy)
def connected_goals(net):
    # Flood physical copper from populated host pads (never from isolated J601).
    rows = [r for r in items if r["net"] == net and r["type"] != "reservation"]
    marked = {i for i,r in enumerate(rows) if r["type"] == "pad" and r["ref"] != "J601"}
    if not marked: raise ValueError("no surviving source pad for "+net)
    changed = True
    while changed:
        changed = False
        for i,r in enumerate(rows):
            if i in marked: continue
            for j in tuple(marked):
                s = rows[j]
                if (r["li"] == s["li"] and r["geom"].distance(s["geom"]) < 0.001) or (
                    r["type"] == "via" and s["type"] == "via" and r["uuid"] == s["uuid"]):
                    marked.add(i); changed = True; break
    return [rows[i] for i in marked]
def route(net, pad, width, escape=False):
    startrow = next(r for r in items if r["type"] == "pad"
        and r["ref"] == "J601" and r["pad"] == str(pad))
    start = startrow["position"]
    sl = startrow["li"]
    goals = [] if escape else connected_goals(net)
    goal = np.zeros((4,NY,NX), dtype=bool)
    obstacle = [None]*4
    free = np.ones_like(goal)
    foreign = [r for r in items if r["net"] != net]
    for li in range(4):
        goal[li] = mask(union([r for r in goals if r["li"] == li]))
        obstacle[li] = union([r for r in foreign if r["li"] == li]).buffer(
            0.15 + width/2 + 0.004)
        free[li] = ~mask(obstacle[li])
    via_obs = union(foreign).buffer(0.15 + 0.225 + 0.015)
    via_free = ~mask(shapely.union_all([via_obs, hole_obstacle]))
    reuse = {tuple(r["position"]) for r in items if r["type"] == "via"
        and r["net"] == net and "position" in r}
    for p in reuse:
        y,x=idx(p)
        if 0<=y<NY and 0<=x<NX and point(y,x)==p:
            via_free[y,x]=True
    if escape:
        goal[sl] = via_free & (abs(xx-start[0])<3.5) & (abs(yy-start[1])<3.5)
    sy,sx = idx(start)
    if not free[sl,sy,sx]: raise ValueError("start is obstructed "+net+"/"+str(pad))
    hdist = distance_transform_edt(~goal.any(axis=0))
    dist = np.full((4,NY,NX), np.inf)
    prev = {}
    state = (sl,sy,sx)
    dist[state] = 0.
    heap = [(float(hdist[sy,sx]),0.,state)]
    moves = [(dy,dx,math.hypot(dy,dx)) for dy in [-1,0,1]
        for dx in [-1,0,1] if dy or dx]
    count = 0
    while heap:
        _,cost,u = heapq.heappop(heap)
        if cost != dist[u]: continue
        li,y,x = u
        count += 1
        if goal[u]: target = u; break
        for dy,dx,dc in moves:
            ny,nx = y+dy,x+dx
            if not (0<=ny<NY and 0<=nx<NX and free[li,ny,nx]): continue
            if dy and dx and not (free[li,y,nx] and free[li,ny,x]): continue
            v=(li,ny,nx)
            nc=cost+dc
            if nc < dist[v]:
                dist[v]=nc; prev[v]=u
                heapq.heappush(heap,(nc+float(hdist[ny,nx]),nc,v))
        if via_free[y,x] and not escape:
            for nl in range(4):
                if nl == li or not free[nl,y,x]: continue
                v=(nl,y,x); nc=cost+100.
                if nc < dist[v]:
                    dist[v]=nc; prev[v]=u
                    heapq.heappush(heap,(nc+float(hdist[y,x]),nc,v))
        if count > 1500000: raise ValueError("route search limit "+net)
    else:
        from PIL import Image, ImageDraw
        im=Image.fromarray(np.uint8(np.where(free[sl],255,0)),"L").convert("RGB")
        draw=ImageDraw.Draw(im)
        draw.ellipse((sx-5,sy-5,sx+5,sy+5),fill="red")
        Image.fromarray(np.uint8(via_free)*255,"L").save("/tmp/panda-via-free.png")
        im.resize((NX*2,NY*2)).save("/tmp/panda-route-blocked.png")
        Path("/tmp/panda-router-partial.json").write_text(json.dumps(
            {"segments":segments,"vias":vias,"net":net,"start":start}))
        raise ValueError("no route "+net+"/"+str(pad)+": states="+str(count)+
            ", goals="+str(goal.sum(axis=(1,2))))
    path=[target]
    while path[-1] != state: path.append(prev[path[-1]])
    path.reverse()
    segs=[]; vs=[point(target[1],target[2])] if escape else []
    pts=[(sl,tuple(start))]+[(li,point(y,x)) for li,y,x in path]
    # Preserve each change of direction, including exact non-grid pad centers.
    i=0
    while i < len(pts)-1:
        li,p=pts[i]; nl,q=pts[i+1]
        if li != nl:
            vs.append(p); i+=1; continue
        if p == q: i+=1; continue
        j=i+1
        last=j
        while last+1 < len(pts) and pts[last+1][0] == li:
            last+=1
        other=union([r for r in foreign if r["li"] == li])
        barrier=other.buffer(0.15+width/2+0.002)
        shapely.prepare(barrier)
        for k in range(last,j,-1):
            r=pts[k][1]
            if not barrier.intersects(LineString([p,r])):
                q=r; j=k; break
        geom=LineString([p,q]).buffer(width/2,quad_segs=12)
        if geom.distance(other) < 0.15-1e-6:
            raise ValueError("trace clearance failed "+net)
        row={"net":net,"layer":native_layers[li],"start":p,"end":q,"width":width}
        segs.append(row)
        items.append({"type":"track","net":net,"li":li,
            "uuid":str(uuid.uuid5(uuid.NAMESPACE_URL,str(row))),"geom":geom,
            "start":p,"end":q})
        i=j
    for p in set(vs)-reuse:
        geom=Point(p).buffer(0.225,quad_segs=24)
        uid=str(uuid.uuid5(uuid.NAMESPACE_URL,net+str(p)))
        for li in range(4):
            items.append({"type":"via","net":net,"li":li,"uuid":uid,"geom":geom,"position":p})
        holes.append(Point(p).buffer(0.125+0.125+0.25+0.01))
        vsrow={"net":net,"position":p,"size":0.45,"drill":0.25}
        vias.append(vsrow)
    segments.extend(segs)
    routes.append({"net":net,"pad":pad,"phase":"escape" if escape else "connect","segments":len(segs),"vias":len(set(vs)-reuse),
        "length_mm":sum(LineString([r["start"],r["end"]]).length for r in segs),
        "search_states":count})
    print(json.dumps(routes[-1]),flush=True)
    return shapely.union_all(holes)

for i,p in [(1,3),(0,1),(2,5),(3,7),(4,9),(5,11)]:
    hole_obstacle=route("EPD_D"+str(i),p,0.15,escape=True)
items=[r for r in items if r["type"] != "reservation"]
for i,p in [(1,3),(0,1),(5,11),(4,9),(3,7),(2,5)]:
    hole_obstacle=route("EPD_D"+str(i),p,0.15)
for p in [35,36]: hole_obstacle=route("3V3_EPD_LOGIC",p,0.20)
for p in list(range(2,35,2))+list(range(55,61)):
    hole_obstacle=route("GND",p,0.20)
data={"routes":routes,"segments":segments,"vias":vias,
    "clearance_mm":0.15,"native_acceptance_required":True}
a.report.write_text(json.dumps(data,indent=2)+"\n")
text=a.pcb.read_text()
addition=[]
for r in segments:
    uid=str(uuid.uuid5(uuid.NAMESPACE_URL,"panda/core-c1/route/"+str(r)))
    addition.append('(segment (start %s %s) (end %s %s) (width %s) (layer "%s") (net "%s") (uuid "%s"))' %
        (*r["start"],*r["end"],r["width"],r["layer"],r["net"],uid))
for r in vias:
    uid=str(uuid.uuid5(uuid.NAMESPACE_URL,"panda/core-c1/via/"+str(r)))
    addition.append('(via (at %s %s) (size %s) (drill %s) (layers "F.Cu" "B.Cu") (net "%s") (uuid "%s"))' %
        (*r["position"],r["size"],r["drill"],r["net"],uid))
end=text.rfind(")")
a.pcb.write_text(text[:end]+"\n"+"\n".join(addition)+"\n"+text[end:])
print("added",len(segments),"segments and",len(vias),"vias")
