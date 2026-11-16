#!/usr/bin/env python3
"""Build an interactive knowledge graph + GraphML/Cypher exports from LLM-wiki data.

Usage: python3 docs/llm-wiki/scripts/build_graph_view.py
Outputs:
  docs/llm-wiki/data/knowledge-graph.json
  docs/llm-wiki/data/graph.graphml
  docs/llm-wiki/data/graph.cypher
  docs/llm-wiki/graph.html
"""
from __future__ import annotations

import html
import json
from collections import Counter
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[3]
WIKI = ROOT / "docs" / "llm-wiki"
DATA = WIKI / "data"

TYPE_LABEL = {
    "requirement": "需求",
    "page": "页面",
    "api": "接口",
    "controller": "控制器",
    "service": "服务",
    "table": "数据表",
}
TYPE_COLOR = {
    "requirement": "#7c3aed",
    "page": "#2563eb",
    "api": "#0f9f6e",
    "controller": "#e07a1c",
    "service": "#c8453c",
    "table": "#475569",
}
EDGE_LABEL = {
    "requirement_has_page": "需求包含页面",
    "requirement_has_api": "需求涉及接口",
    "page_calls_api": "页面调用接口",
    "handled_by": "由控制器处理",
    "calls_service": "调用服务",
    "accesses_table": "访问数据表",
}


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def enrich() -> dict:
    graph = read_json(DATA / "graph.json")
    apis = {item["id"]: item for item in read_json(DATA / "apis.json")["items"]}
    pages = {item["id"]: item for item in read_json(DATA / "pages.json")["items"]}
    requirements = {item["id"]: item for item in read_json(DATA / "requirements.json")["items"]}
    degree = Counter()
    for edge in graph["edges"]:
        degree[edge["from"]] += 1
        degree[edge["to"]] += 1
    nodes = []
    for node in graph["nodes"]:
        props: dict = {"degree": degree[node["id"]]}
        if node["type"] == "api":
            item = apis.get(node["id"], {})
            props.update({
                "method": item.get("method", ""),
                "path": item.get("path", ""),
                "summary": item.get("summary", ""),
                "auth": item.get("auth", ""),
                "controller": item.get("controller", ""),
                "services": item.get("services", []),
                "tables": item.get("tables", []),
            })
        elif node["type"] == "page":
            item = pages.get(node["id"], {})
            props.update({
                "area": item.get("area", ""),
                "route": item.get("deployed_path") or item.get("route", ""),
                "view": item.get("view", ""),
            })
        elif node["type"] == "requirement":
            item = requirements.get(node["id"], {})
            props.update({
                "version": item.get("version", ""),
                "module": item.get("module", ""),
                "priority": item.get("priority", ""),
                "section": item.get("section", ""),
            })
        nodes.append({
            "id": node["id"],
            "type": node["type"],
            "typeLabel": TYPE_LABEL.get(node["type"], node["type"]),
            "label": node["label"],
            "properties": props,
        })
    edges = [
        {
            "source": edge["from"],
            "target": edge["to"],
            "type": edge["type"],
            "label": EDGE_LABEL.get(edge["type"], edge["type"]),
        }
        for edge in graph["edges"]
    ]
    return {
        "meta": {
            "title": "尚品汇 LLM-wiki 知识图谱",
            "nodes": len(nodes),
            "edges": len(edges),
            "nodeTypes": dict(Counter(node["type"] for node in nodes)),
            "edgeTypes": dict(Counter(edge["type"] for edge in edges)),
        },
        "nodes": nodes,
        "edges": edges,
    }


def write_graphml(graph: dict) -> None:
    root = ET.Element("graphml", xmlns="http://graphml.graphdrawing.org/xmlns")
    for key, attr_type in (("label", "string"), ("type", "string"), ("typeLabel", "string")):
        ET.SubElement(root, "key", id=key, **{"for": "node", "attr.name": key, "attr.type": attr_type})
    ET.SubElement(root, "key", id="relation", **{"for": "edge", "attr.name": "relation", "attr.type": "string"})
    graph_el = ET.SubElement(root, "graph", id="shang-pivot-llm-wiki", edgedefault="directed")
    for node in graph["nodes"]:
        node_el = ET.SubElement(graph_el, "node", id=node["id"])
        for key, value in (("label", node["label"]), ("type", node["type"]), ("typeLabel", node["typeLabel"])):
            data = ET.SubElement(node_el, "data", key=key)
            data.text = str(value)
    for index, edge in enumerate(graph["edges"]):
        edge_el = ET.SubElement(
            graph_el,
            "edge",
            id=f"e{index}",
            source=edge["source"],
            target=edge["target"],
        )
        data = ET.SubElement(edge_el, "data", key="relation")
        data.text = edge["label"]
    ET.ElementTree(root).write(DATA / "graph.graphml", encoding="utf-8", xml_declaration=True)


def cypher_quote(value: object) -> str:
    return str(value).replace("\\", "\\\\").replace("'", "\\'")


def write_cypher(graph: dict) -> None:
    labels = {
        "requirement": "Requirement",
        "page": "Page",
        "api": "Api",
        "controller": "Controller",
        "service": "Service",
        "table": "Table",
    }
    rel_types = {
        "requirement_has_page": "REQUIREMENT_HAS_PAGE",
        "requirement_has_api": "REQUIREMENT_HAS_API",
        "page_calls_api": "PAGE_CALLS_API",
        "handled_by": "HANDLED_BY",
        "calls_service": "CALLS_SERVICE",
        "accesses_table": "ACCESSES_TABLE",
    }
    lines = ["// ShangPivot LLM-wiki knowledge graph", "// Run in Neo4j Browser or cypher-shell.", ""]
    for node in graph["nodes"]:
        label = labels.get(node["type"], "Node")
        lines.append(
            f"MERGE (n:{label} {{id: '{cypher_quote(node['id'])}'}}) "
            f"SET n.label = '{cypher_quote(node['label'])}', n.type = '{cypher_quote(node['type'])}';"
        )
    lines.append("")
    for edge in graph["edges"]:
        rel = rel_types.get(edge["type"], "RELATED_TO")
        lines.append(
            f"MATCH (a {{id: '{cypher_quote(edge['source'])}'}}), (b {{id: '{cypher_quote(edge['target'])}'}}) "
            f"MERGE (a)-[:{rel}]->(b);"
        )
    (DATA / "graph.cypher").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_html(graph: dict) -> None:
    payload = json.dumps(graph, ensure_ascii=False).replace("</", "<\\/")
    template = """<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>尚品汇 LLM-wiki 知识图谱</title>
<style>
:root{--bg:#f4f6fb;--panel:#fff;--line:#e3e8f0;--text:#172033;--muted:#6b7280}
*{box-sizing:border-box} body{margin:0;background:var(--bg);color:var(--text);font:13px/1.5 -apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei",sans-serif}
header{height:64px;background:#0f172a;color:#fff;display:flex;align-items:center;justify-content:space-between;padding:0 22px;gap:18px}
.brand{display:flex;align-items:center;gap:10px}.mark{width:34px;height:34px;border-radius:9px;background:linear-gradient(135deg,#2563eb,#7c3aed);display:grid;place-items:center;font-weight:800;font-size:11px}
h1{font-size:15px;margin:0}.sub{font-size:11px;color:#94a3b8;margin-top:2px}.stats{display:flex;gap:16px;font-size:11px;color:#cbd5e1}.stats b{color:#fff;font-size:15px;display:block}
.layout{display:grid;grid-template-columns:240px minmax(0,1fr) 340px;height:calc(100vh - 64px)}
aside{background:#fff;border-right:1px solid var(--line);padding:16px;overflow:auto}.right{border-right:0;border-left:1px solid var(--line)}
h2{font-size:11px;text-transform:uppercase;letter-spacing:.08em;color:var(--muted);margin:0 0 9px}
input{width:100%;height:34px;border:1px solid var(--line);border-radius:8px;padding:0 10px;outline:none;font-size:12px}input:focus{border-color:#2563eb;box-shadow:0 0 0 3px #dbeafe}
.legend{margin-top:18px}.legend-row{display:flex;align-items:center;gap:8px;padding:6px 0;font-size:12px;color:#475569}.dot{width:9px;height:9px;border-radius:50%;flex:none}.count{margin-left:auto;color:#94a3b8;font-size:11px}
.hint{font-size:11px;color:var(--muted);line-height:1.7;margin-top:16px;border-top:1px solid var(--line);padding-top:12px}
#canvas-scroll{overflow:auto;background:radial-gradient(#e8edf7 1px,transparent 1px);background-size:22px 22px}
svg{display:block;min-width:100%;background:transparent}.node{cursor:pointer}.node rect{stroke:#fff;stroke-width:1.5}.node text{font:11px -apple-system,PingFang SC,sans-serif;fill:#334155;pointer-events:none}.node .type{font-size:9px;fill:#64748b}.edge{stroke:#cbd5e1;stroke-opacity:.24;stroke-width:1}.edge.highlight{stroke:#60a5fa;stroke-opacity:.9;stroke-width:1.5}
.detail{font-size:12px}.detail h3{font-size:14px;margin:0 0 4px;word-break:break-all}.detail .id{font:11px/1.5 ui-monospace,Menlo,monospace;color:var(--muted);word-break:break-all}.badge{display:inline-flex;padding:2px 7px;border-radius:999px;font-size:10px;color:#fff;margin-top:8px}
.kv{margin-top:12px;border-top:1px solid var(--line)}.kv-row{display:grid;grid-template-columns:90px 1fr;gap:8px;padding:7px 0;border-bottom:1px solid #f1f4f9;font-size:11px}.kv-row .k{color:var(--muted)}.kv-row .v{word-break:break-word}
.neighbors{margin-top:14px}.neighbor{display:block;padding:6px 0;border-bottom:1px solid #f1f4f9;font-size:11px;color:#475569;cursor:pointer}.neighbor:hover{color:#2563eb}.neighbor small{color:#94a3b8;display:block}.empty{padding:30px 0;text-align:center;color:#94a3b8;font-size:12px}
.column-label{font-size:11px;font-weight:600;fill:#64748b;letter-spacing:.05em}
</style>
</head>
<body>
<header><div class="brand"><div class="mark">KG</div><div><h1>尚品汇 LLM-wiki 知识图谱</h1><div class="sub">需求 / 页面 / 接口 / 控制器 / 服务 / 数据表</div></div></div><div class="stats"><div><b>__NODE_COUNT__</b>节点</div><div><b>__EDGE_COUNT__</b>关系</div><div><b>__TYPE_COUNT__</b>类型</div></div></header>
<div class="layout">
<aside><h2>搜索节点</h2><input id="search" placeholder="搜索标题 / ID / 路径" autocomplete="off"/><div class="legend" id="legend"></div><div class="hint">按类型分列展示；点击节点查看属性、关系和邻居。<br/>滚轮/触控板横向滚动查看完整图谱。</div></aside>
<div id="canvas-scroll"><svg id="svg"></svg></div>
<aside class="right"><h2>节点详情</h2><div id="detail" class="detail"><div class="empty">点击一个节点查看属性、关系和邻居</div></div></aside>
</div>
<script id="graph-data" type="application/json">__PAYLOAD__</script>
<script>
const graph=JSON.parse(document.getElementById('graph-data').textContent);
const colors=__COLORS__;
const labels=__LABELS__;
const order=['requirement','page','api','controller','service','table'];
const x={requirement:10,page:180,api:345,controller:545,service:690,table:820};
const w={requirement:160,page:150,api:185,controller:130,service:110,table:145};
const groups={};order.forEach(t=>groups[t]=[]);graph.nodes.forEach(n=>groups[n.type].push(n));
order.forEach(t=>groups[t].sort((a,b)=>a.label.localeCompare(b.label,'zh-CN')));
const pos={};order.forEach(t=>groups[t].forEach((n,i)=>pos[n.id]={x:x[t],y:80+i*22,w:w[t],h:17}));
const height=Math.max(900,...order.map(t=>100+groups[t].length*22+80));
const width=985;
const byId=new Map(graph.nodes.map(n=>[n.id,n]));
const svg=document.getElementById('svg');svg.setAttribute('viewBox',`0 0 ${width} ${height}`);svg.setAttribute('width',width);svg.setAttribute('height',height);
const ns='http://www.w3.org/2000/svg';const mk=(tag,attrs={})=>{const e=document.createElementNS(ns,tag);for(const[k,v]of Object.entries(attrs))e.setAttribute(k,v);return e;};
order.forEach(t=>{const label=mk('text',{x:x[t],y:38,'class':'column-label'});label.textContent=`${labels[t]} (${groups[t].length})`;svg.appendChild(label);});
const edgeLayer=mk('g'),nodeLayer=mk('g');svg.append(edgeLayer,nodeLayer);
const edgeEls=[];
graph.edges.forEach(e=>{const a=pos[e.source],b=pos[e.target];if(!a||!b)return;const line=mk('line',{x1:a.x+a.w,y1:a.y+a.h/2,x2:b.x,y2:b.y+b.h/2,'class':'edge','data-source':e.source,'data-target':e.target});line.dataset.label=e.label;edgeLayer.appendChild(line);edgeEls.push(line);});
const nodeEls=new Map();
graph.nodes.forEach(n=>{const p=pos[n.id];const g=mk('g',{'class':'node','data-id':n.id});g.appendChild(mk('rect',{x:p.x,y:p.y,width:p.w,height:p.h,rx:4,fill:colors[n.type]||'#64748b',opacity:.92}));const txt=mk('text',{x:p.x+7,y:p.y+12});txt.textContent=n.label.length>((p.w-14)/11)?n.label.slice(0,Math.floor((p.w-14)/11)-1)+'…':n.label;g.appendChild(txt);const title=mk('title');title.textContent=`${n.typeLabel} · ${n.label}\n${n.id}`;g.appendChild(title);g.addEventListener('click',()=>detail(n));nodeLayer.appendChild(g);nodeEls.set(n.id,g);});
let selected=null,query='';const activeTypes=new Set(order);
function esc(s){return String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
function detail(n){const box=document.getElementById('detail');if(!n){box.innerHTML='<div class="empty">点击一个节点查看属性、关系和邻居</div>';return;}const rels=edgeEls.filter(e=>e.dataset.source===n.id||e.dataset.target===n.id);let props='';for(const[k,v]of Object.entries(n.properties||{})){if(v==null||v===''||(Array.isArray(v)&&!v.length))continue;props+=`<div class="kv-row"><span class="k">${esc(k)}</span><span class="v">${esc(Array.isArray(v)?v.join(', '):v)}</span></div>`;}box.innerHTML=`<h3>${esc(n.label)}</h3><div class="id">${esc(n.id)}</div><span class="badge" style="background:${colors[n.type]||'#64748b'}">${esc(n.typeLabel)}</span><div class="kv">${props}</div><div class="neighbors"><h2 style="margin-top:14px">关联关系（${rels.length}）</h2>${rels.slice(0,40).map(e=>{const other=e.dataset.source===n.id?e.dataset.target:e.dataset.source;const o=byId.get(other);return `<span class="neighbor" data-id="${esc(other)}">${esc(e.dataset.label)} → ${esc(o?o.label:other)}<small>${esc(other)}</small></span>`;}).join('')}</div>`;box.querySelectorAll('.neighbor').forEach(el=>el.onclick=()=>{selected=byId.get(el.dataset.id);detail(selected);mark();});}
function mark(){const q=query.toLowerCase();nodeEls.forEach((el,id)=>{const n=byId.get(id);const hit=!q||n.label.toLowerCase().includes(q)||id.toLowerCase().includes(q);el.style.display=activeTypes.has(n.type)?'':'none';el.style.opacity=hit?1:.18;el.querySelector('rect').setAttribute('stroke',selected&&selected.id===id?'#0f172a':'#fff');el.querySelector('rect').setAttribute('stroke-width',selected&&selected.id===id?3:1.5);});edgeEls.forEach(e=>{const s=byId.get(e.dataset.source),t=byId.get(e.dataset.target);const on=activeTypes.has(s.type)&&activeTypes.has(t.type);const hit=!q||s.label.toLowerCase().includes(q)||t.label.toLowerCase().includes(q);e.style.display=on?'':'none';e.classList.toggle('highlight',!!selected&&(e.dataset.source===selected.id||e.dataset.target===selected.id));e.style.opacity=hit?'':'0.05';});}
function legend(){document.getElementById('legend').innerHTML=order.map(t=>`<label class="legend-row"><input type="checkbox" checked data-type="${t}"/><span class="dot" style="background:${colors[t]}"></span>${labels[t]}<span class="count">${groups[t].length}</span></label>`).join('');document.querySelectorAll('[data-type]').forEach(cb=>cb.onchange=()=>{cb.checked?activeTypes.add(cb.dataset.type):activeTypes.delete(cb.dataset.type);mark();});}
document.getElementById('search').oninput=e=>{query=e.target.value.trim();mark();};legend();mark();
</script>
</body>
</html>"""
    colors = "{" + ",".join(f"{key}:'{value}'" for key, value in TYPE_COLOR.items()) + "}"
    labels = "{" + ",".join(f"{key}:'{value}'" for key, value in TYPE_LABEL.items()) + "}"
    html_text = (
        template
        .replace("__PAYLOAD__", payload)
        .replace("__NODE_COUNT__", str(graph["meta"]["nodes"]))
        .replace("__EDGE_COUNT__", str(graph["meta"]["edges"]))
        .replace("__TYPE_COUNT__", str(len(graph["meta"]["nodeTypes"])))
        .replace("__COLORS__", colors)
        .replace("__LABELS__", labels)
    )
    (WIKI / "graph.html").write_text(html_text, encoding="utf-8")

def main() -> int:
    graph = enrich()
    (DATA / "knowledge-graph.json").write_text(json.dumps(graph, ensure_ascii=False, indent=2), encoding="utf-8")
    write_graphml(graph)
    write_cypher(graph)
    write_html(graph)
    print(json.dumps(graph["meta"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
