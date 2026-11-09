"use strict";
// 所有动态内容都经 esc() 转义后再插入，防止 OCR 文本、字段名等造成脚本注入。
const $ = (s) => document.querySelector(s);
const esc = (v) => String(v ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const pct = (x) => (x == null ? "—" : (x * 100).toFixed(1) + "%");

async function api(path, body) {
  const opt = body === undefined ? {} : { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) };
  const r = await fetch(path, opt);
  const text = await r.text();
  let data;
  try { data = JSON.parse(text); } catch { data = text; }
  if (!r.ok) throw new Error((data && data.detail) || text || r.statusText);
  return data;
}

// ------------------------------------------------------------------ tabs
const tabs = ["build", "onto", "qa"];
function selectTab(name) {
  for (const t of tabs) {
    const on = t === name;
    $(`#tab-${t}`).setAttribute("aria-selected", on);
    $(`#tab-${t}`).tabIndex = on ? 0 : -1;
    $(`#panel-${t}`).hidden = !on;
  }
  if (name === "onto") loadOntology();
  if (name === "qa") loadSamples();
}
tabs.forEach((t, i) => {
  const b = $(`#tab-${t}`);
  b.addEventListener("click", () => selectTab(t));
  b.addEventListener("keydown", (e) => {
    if (e.key !== "ArrowRight" && e.key !== "ArrowLeft") return;
    const next = tabs[(i + (e.key === "ArrowRight" ? 1 : tabs.length - 1)) % tabs.length];
    selectTab(next); $(`#tab-${next}`).focus();
  });
});

// ------------------------------------------------------------------ status
async function refreshStatus() {
  try {
    const s = await api("/api/status");
    const w = s.ontowing, m = s.mysql;
    if (s.public) { $("#btn-mysql").hidden = true; $("#mysql-msg").textContent = "公网演示模式：已禁用建库，构建每 60 秒限一次。"; }
    const dbs = Object.entries(m.databases || {}).map(([k, v]) => `${k}:${v}`).join(" ");
    $("#status").innerHTML = [
      `OntoWing：${w.available ? `<span class="badge ok">可用</span> ${esc(w.commit)}` : `<span class="badge bad">不可用</span> ${esc(w.error)}`}`,
      `MySQL：${!m.configured ? '<span class="badge warn">未配置 .env</span>' : m.connected ? `<span class="badge ok">已连接</span> ${esc(m.target || "")} ${esc(dbs || "（未建库）")}` : `<span class="badge bad">连接失败</span> ${esc(m.error || "")}`}`,
      `沙箱数据：${s.sandbox ? '<span class="badge ok">就绪</span>' : '<span class="badge warn">缺失</span>'}`,
    ].join("<br>");
  } catch (e) { $("#status").textContent = "服务不可用：" + e.message; }
}

// ------------------------------------------------------------------ 1 构建
$("#btn-mysql").addEventListener("click", async (ev) => {
  const btn = ev.currentTarget; btn.disabled = true;
  $("#mysql-msg").textContent = "建库中…";
  try {
    const r = await api("/api/mysql/init", {});
    $("#mysql-msg").innerHTML = '<span class="badge ok">完成</span> ' + Object.entries(r.created_tables).map(([k, v]) => `${esc(k)} ${v} 张表`).join("，");
    refreshStatus();
  } catch (e) { $("#mysql-msg").innerHTML = `<span class="badge bad">失败</span> ${esc(e.message)}`; }
  btn.disabled = false;
});

$("#btn-build").addEventListener("click", async (ev) => {
  const btn = ev.currentTarget; btn.disabled = true;
  $("#build-out").innerHTML = '<div class="card">构建中…（执行 R2RML 约需 30 秒）</div>';
  try {
    const r = await api("/api/build", { source: $("#build-source").value, execute_r2rml: $("#opt-r2rml").checked, evaluate: $("#opt-eval").checked });
    $("#build-out").innerHTML = renderBuild(r);
    ontoLoaded = false; refreshStatus();
  } catch (e) { $("#build-out").innerHTML = `<div class="card"><span class="badge bad">失败</span> ${esc(e.message)}</div>`; }
  btn.disabled = false;
});

function renderBuild(r) {
  const s = r.summary;
  const steps = r.steps.map((x) => `<li>${x.ok ? '<span class="badge ok">通过</span>' : '<span class="badge bad">失败</span>'} ${esc(x.step)} <span class="hint">${x.seconds}s</span>${renderDetail(x.detail)}</li>`).join("");
  let html = `<div class="card"><h2>构建步骤</h2><ol class="steps">${steps}</ol></div>`;
  html += `<div class="card"><h2>本体规模</h2><div class="grid">
    ${metric(s.abstract_classes, "上位类")}${metric(s.concepts, "业务对象")}${metric(s.derived_classes, "派生类")}
    ${metric(s.attributes, "属性")}${metric(s.relations, "关系（含反向）")}${metric(s.rules, "规则")}${metric(s.constraints, "约束")}
    ${metric(s.bindings, "数据管道绑定")}${metric(s.tables_in_scope, "纳入的源表")}${metric(s.tables_excluded.length, "剔除的噪声表")}</div>
    <p class="hint">元数据来源：${esc(s.metadata_source === "mysql" ? "MySQL information_schema" : "DDL 文件")}；OntoWing ${esc(r.ontowing.commit)}${r.ontowing.backend ? `（${esc(r.ontowing.backend)}）` : ""}</p></div>`;
  const wv = r.wing_validation;
  html += `<div class="card"><h2>OntoWing 静态校验</h2><table><thead><tr><th>对象</th><th>结果</th><th>检查项</th><th>诊断</th></tr></thead><tbody>
    ${["model", "pipeline", "rules"].map((k) => `<tr><td>${{ model: "本体（wing-model-editor/1）", pipeline: "数据管道映射（wing-pipeline-editor/2）", rules: "规则与约束（wing-rules-editor/2）" }[k]}</td>
    <td>${wv[k].valid ? '<span class="badge ok">有效</span>' : '<span class="badge bad">无效</span>'}</td>
    <td class="mono">${esc(JSON.stringify(wv[k].checks || {}))}</td><td>${wv[k].diagnostics.length ? esc(wv[k].diagnostics.map((d) => d.code).join("、")) : "无"}</td></tr>`).join("")}
    </tbody></table></div>`;
  if (r.r2rml_execution && r.r2rml_execution.ran) {
    const x = r.r2rml_execution;
    html += `<div class="card"><h2>R2RML 实跑（Morph-KGC，沙箱数据）</h2>
      <p>${x.passed ? '<span class="badge ok">通过</span>' : '<span class="badge bad">未通过</span>'} 生成三元组 ${x.triples.toLocaleString()} 个；空概念 ${x.empty_concepts.length} 个；悬空引用 ${x.dangling_total} 个${x.errors.length ? "；错误：" + esc(x.errors.join("；")) : ""}</p>
      <table><thead><tr><th>概念</th><th>实例数</th></tr></thead><tbody>${Object.entries(x.instances_by_concept).map(([k, v]) => `<tr><td>${esc(k)}</td><td>${v.toLocaleString()}</td></tr>`).join("")}</tbody></table></div>`;
  }
  if (r.reasoning) {
    const x = r.reasoning;
    html += `<div class="card"><h2>规则推理（在 R2RML 实例图上执行 OntoWing 导出的 SWRL）</h2>
      <p>${x.passed ? '<span class="badge ok">与独立 SQL 口径一致</span>' : '<span class="badge bad">不一致</span>'} 前向链 ${x.rounds} 轮到不动点。每条规则的推理结果都用一条独立 SQL 在原始库上重算核对。</p>
      <table><thead><tr><th>规则</th><th>级别</th><th>推理得出</th><th>SQL 核对</th><th>结果</th></tr></thead><tbody>
      ${x.rules.map((y) => `<tr><td>${esc(y.name)}</td><td>${y.level === "FR" ? "事实规则" : "建议规则"}</td><td>${y.inferred ?? "—（不导出）"}</td><td>${y.sql_check}</td><td>${y.match === null ? '<span class="badge info">仅供人工参考</span>' : y.match ? '<span class="badge ok">一致</span>' : '<span class="badge bad">不一致</span>'}</td></tr>`).join("")}
      </tbody></table>
      <h3>约束检查（OntoWing 约束，在实例上执行）</h3>
      <table><thead><tr><th>约束</th><th>检查实例</th><th>违反</th></tr></thead><tbody>
      ${x.constraints.map((c) => `<tr><td>${esc(c.name)}</td><td>${c.checked.toLocaleString()}</td><td>${c.violations ? `<span class="badge warn">${c.violations}</span>` : '<span class="badge ok">0</span>'}</td></tr>`).join("")}
      </tbody></table></div>`;
  }
  html += `<div class="card"><h2>关系推断依据</h2><table><thead><tr><th>关系</th><th>外键</th><th>依据</th></tr></thead><tbody>
    ${r.relations.map((x) => `<tr><td>${esc(x.name)}</td><td class="mono">${esc(x.child)}.${esc(x.child_col)} → ${esc(x.parent)}.${esc(x.parent_col)}</td><td>${x.provenance.map((p) => `<span class="badge info">${esc(provName(p))}</span>`).join(" ")}</td></tr>`).join("")}
    </tbody></table>
    <h3>其他构建决策</h3><ul class="steps">${r.decisions.map((d) => `<li>${esc(decisionText(d))}</li>`).join("")}</ul></div>`;
  if (r.evaluation) html += renderEval(r.evaluation);
  return html;
}
function metric(v, label) { return `<div class="metric"><b>${esc(v)}</b><span>${esc(label)}</span></div>`; }
function provName(p) { return { naming_convention: "命名约定", task_sql_join: "任务 SQL 关联", hot_sql_join: "热点 SQL 关联", dataworks_export: "DataWorks 导出", task_sql: "任务 SQL 解析" }[p] || p; }
function decisionText(d) {
  if (d.type === "exclude_table") return `剔除 ${d.table}：${d.reason}`;
  if (d.type === "merge_tables") return `合并 ${d.tables.join("、")} 为概念 ${d.concept}：${d.reason}`;
  if (d.type === "identity_key") return `概念 ${d.concept} 以 ${d.key.join(",")} 作为实体标识：${d.reason}`;
  if (d.type === "link_table") return `关联表 ${d.table}：${d.reason}`;
  if (d.type === "rule_skipped") return `跳过规则/约束 ${d.rule || d.constraint}：${d.reason}`;
  return JSON.stringify(d);
}
function renderDetail(d) {
  if (!d) return "";
  if (d.log) return `<ul class="path">${d.log.map((l) => `<li>${esc(l)}</li>`).join("")}</ul>`;
  const keep = Object.entries(d).filter(([k]) => !["diagnostics", "instances_by_concept"].includes(k));
  return `<div class="hint mono">${esc(keep.map(([k, v]) => `${k}=${typeof v === "object" ? JSON.stringify(v) : v}`).join("  "))}</div>`;
}
function renderEval(e) {
  const row = (name, o) => `<tr><td>${esc(name)}</td><td>${o.n}</td><td>${pct(o.strict)}</td><td>${pct(o.lenient)}</td><td>${pct(o.abstain)}</td></tr>`;
  let rows = row("本系统（开发集）", e.system.overall) + row("本系统（留出集）", e.holdout.overall)
    + row("基线：DDL 注释关键词匹配（开发集）", e.baseline_keyword.overall) + row("基线：DDL 注释关键词匹配（留出集）", e.holdout.baseline_keyword);
  const names = { no_synonyms: "消融：去掉领域同义词", no_value_check: "消融：去掉原始数据值校验", no_platform_lineage: "消融：不走中台血缘", export_lineage_only: "消融：只用 DataWorks 导出血缘（不解析任务 SQL）" };
  for (const [k, v] of Object.entries(e.ablations || {})) rows += row(names[k] || k, v);
  const groups = Object.entries(e.system.by_group).map(([k, v]) => row(k.replace("derivation:", "派生类型：").replace("context:", "截图上下文：").replace("page:", "页面："), v)).join("");
  const misses = e.misses.length ? `<table><thead><tr><th>需求</th><th>字段</th><th>预测</th><th>答案</th></tr></thead><tbody>${e.misses.map((m) => `<tr><td>${esc(m.request_id)}</td><td>${esc(m.label)}</td><td class="mono">${esc(m.predicted.join("; ") || "（待确认）")}</td><td class="mono">${esc(m.expected.join("; "))}</td></tr>`).join("")}</tbody></table>` : "<p>无</p>";
  return `<div class="card"><h2>评测（对照 data/gold 标准答案）</h2>
    <p class="hint">严格：源字段集合与答案完全一致；宽松：命中答案或其等价字段（如工单客户编号 ↔ 营销户号）。待确认不计为答对。留出集为调优期间未使用的新页面和新叫法。</p>
    <table><thead><tr><th>方案</th><th>字段数</th><th>严格</th><th>宽松</th><th>待确认</th></tr></thead><tbody>${rows}</tbody></table>
    <details><summary>开发集分组</summary><table><thead><tr><th>分组</th><th>字段数</th><th>严格</th><th>宽松</th><th>待确认</th></tr></thead><tbody>${groups}</tbody></table></details>
    <h3>错例</h3>${misses}</div>`;
}

// ------------------------------------------------------------------ 2 本体
// 分层图：上位类（顶层）→ 具体概念（中层，有物理表）→ 规则派生类（底层）；规则作为菱形节点连接“用到的类”和“推出的类”。
let ontoLoaded = false, ontoData = null, layers = { isa: true, relation: true, rule: true };
async function loadOntology() {
  if (ontoLoaded) return;
  $("#concept-detail").innerHTML = '<p class="hint">加载中…（首次会在后台构建本体）</p>';
  try {
    ontoData = await api("/api/ontology");
    ontoLoaded = true;
    renderOntoSummary(ontoData);
    drawGraph(ontoData);
    const kinds = { abstract: "上位类", concrete: "业务对象", derived: "派生类（规则）" };
    $("#concept-list").innerHTML = ["abstract", "concrete", "derived"].map((k) =>
      `<li class="group">${kinds[k]}：</li>` + ontoData.nodes.filter((n) => n.kind === k).map((n) => `<li><button type="button" data-id="${esc(n.id)}" aria-pressed="false">${esc(n.label)}</button></li>`).join("")).join("")
      + `<li class="group">规则：</li>` + ontoData.rules.map((r) => `<li><button type="button" data-rule="${esc(r.id)}" aria-pressed="false">◆ ${esc(r.name)}</button></li>`).join("");
    $("#concept-list").querySelectorAll("button[data-id]").forEach((b) => b.addEventListener("click", () => showConcept(b.dataset.id)));
    $("#concept-list").querySelectorAll("button[data-rule]").forEach((b) => b.addEventListener("click", () => showRule(b.dataset.rule)));
    showConcept("Consumer");
    loadArtifactLinks();
  } catch (e) { $("#concept-detail").innerHTML = `<span class="badge bad">失败</span> ${esc(e.message)}`; }
}
document.querySelectorAll("#layer-toggles input").forEach((cb) => cb.addEventListener("change", () => { layers[cb.value] = cb.checked; drawGraph(ontoData); }));

function renderOntoSummary(g) {
  const c = (k) => g.nodes.filter((n) => n.kind === k).length;
  const rel = g.edges.filter((e) => e.kind === "relation").length, isa = g.edges.filter((e) => e.kind === "subclass").length;
  $("#onto-summary").innerHTML = `上位类 <b>${c("abstract")}</b> ｜ 业务对象 <b>${c("concrete")}</b> ｜ 派生类 <b>${c("derived")}</b> ｜ 关系 <b>${rel}</b>（另有反向关系） ｜ 继承 <b>${isa}</b> ｜ 规则 <b>${g.rules.length}</b>`;
}
function sysOf(n) {
  if (n.kind !== "concrete") return n.kind;
  const t = n.tables[0] || ""; return t.split(".")[0];
}
const nodeW = (n) => Math.max(76, n.label.length * 13 + 16);

function layout(g, W) {
  // 每个上位类一列：上位类在列顶，其业务对象在下方纵向排列；规则与派生类在底部，对齐到其父对象所在列
  const byId = Object.fromEntries(g.nodes.map((n) => [n.id, n]));
  const tops = g.nodes.filter((n) => n.kind === "abstract");
  const concrete = g.nodes.filter((n) => n.kind === "concrete");
  const derived = g.nodes.filter((n) => n.kind === "derived");
  const cols = tops.map((t) => ({ top: t, kids: concrete.filter((c) => c.parents.includes(t.id)) }));
  const orphans = concrete.filter((c) => !cols.some((col) => col.kids.includes(c)));
  if (orphans.length) cols.push({ top: null, kids: orphans });
  const colW = (W - 40) / cols.length;
  cols.forEach((col, i) => {
    const cx = 20 + colW * (i + 0.5);
    if (col.top) { col.top.x = cx; col.top.y = 50; }
    col.kids.forEach((k, j) => { k.x = cx; k.y = 130 + j * 62; });
  });
  for (const d of derived) { const p = byId[d.parents[0]]; d.x = p ? p.x : W / 2; d.y = 580; }
  spread(derived, W);
  const rules = g.rules.map((r) => ({ ...r, kind: "rule", label: r.name.replace("认定", "") }));
  for (const r of rules) { const h = byId[r.head]; r.x = h ? h.x : W / 2; r.y = 480; }
  spread(rules, W);
  return { byId, rules };
}
function spread(list, W) {
  list.sort((a, b) => a.x - b.x);
  for (let it = 0; it < 50; it++) {
    for (let i = 1; i < list.length; i++) {
      const a = list[i - 1], b = list[i], need = (nodeW(a) + nodeW(b)) / 2 + 14 - (b.x - a.x);
      if (need > 0) { a.x -= need / 2; b.x += need / 2; }
    }
    for (const n of list) n.x = Math.min(W - nodeW(n) / 2 - 6, Math.max(nodeW(n) / 2 + 6, n.x));
  }
}
function curve(a, b, bend) {
  const mx = (a.x + b.x) / 2, my = (a.y + b.y) / 2 - bend;
  return `M${a.x},${a.y} Q${mx},${my} ${b.x},${b.y}`;
}
function drawGraph(g) {
  const svg = $("#graph"); const W = Math.max(svg.clientWidth || 1100, 1000), H = 630;
  svg.setAttribute("viewBox", `0 0 ${W} ${H}`);
  const { byId, rules } = layout(g, W);
  let s = `<defs>
    <marker id="arr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="#7d8798"/></marker>
    <marker id="tri" viewBox="0 0 12 12" refX="11" refY="6" markerWidth="10" markerHeight="10" orient="auto"><path d="M0,0 L12,6 L0,12 z" fill="#fff" stroke="#3a4252"/></marker>
    <marker id="arr-rule" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#b25b00"/></marker></defs>`;
  s += `<text class="band" x="8" y="18">上位类（领域分类）</text><text class="band" x="8" y="100">业务对象（映射到物理表）</text><text class="band" x="8" y="452">规则</text><text class="band" x="8" y="552">派生类（由规则推出）</text>`;
  const edgeEnd = (a, b) => { const dy = b.y - a.y; return { x: b.x, y: b.y - Math.sign(dy) * 16 }; };
  if (layers.isa) for (const e of g.edges.filter((e) => e.kind === "subclass")) {
    const a = byId[e.source], b = byId[e.target]; if (!a || !b) continue;
    s += `<path class="edge isa" data-s="${esc(a.id)}" data-t="${esc(b.id)}" d="M${a.x},${a.y - 15} L${b.x},${b.y + 16}" marker-end="url(#tri)"><title>${esc(a.label)} 是一种 ${esc(b.label)}</title></path>`;
  }
  if (layers.relation) for (const e of g.edges.filter((e) => e.kind === "relation" || e.kind === "identity")) {
    const a = byId[e.source], b = byId[e.target]; if (!a || !b) continue;
    if (a === b) {
      s += `<path class="edge rel" data-s="${esc(a.id)}" data-t="${esc(b.id)}" d="M${a.x + 20},${a.y - 15} C${a.x + 55},${a.y - 60} ${a.x - 55},${a.y - 60} ${a.x - 20},${a.y - 15}" marker-end="url(#arr)"><title>${esc(e.label)}</title></path>`;
      continue;
    }
    let d;
    if (Math.abs(a.x - b.x) < 1) {
      const side = nodeW(a) / 2 + 6, off = 18 + Math.abs(a.y - b.y) * 0.25;
      d = `M${a.x + side},${a.y} C${a.x + side + off},${a.y} ${b.x + side + off},${b.y} ${b.x + side},${b.y}`;
    } else {
      const sx = a.x + Math.sign(b.x - a.x) * nodeW(a) / 2, ex = b.x - Math.sign(b.x - a.x) * nodeW(b) / 2;
      const bend = a.y === b.y ? 26 : 0;
      d = curve({ x: sx, y: a.y }, { x: ex, y: b.y }, bend);
    }
    s += `<path class="edge rel" data-s="${esc(a.id)}" data-t="${esc(b.id)}" d="${d}" marker-end="url(#arr)"><title>${esc(a.label)} —${esc(e.label)}→ ${esc(b.label)}${e.inverse_label ? "（反向：" + esc(e.inverse_label) + "）" : ""}</title></path>`;
  }
  if (layers.rule) for (const r of rules) {
    for (const u of r.uses) { const a = byId[u]; if (a) s += `<path class="edge rule-in" data-rule="${esc(r.id)}" d="${curve(a, { x: r.x, y: r.y - 14 }, 0)}"><title>${esc(r.name)} 使用 ${esc(a.label)}</title></path>`; }
    const h = byId[r.head]; if (h) s += `<path class="edge rule-out" data-rule="${esc(r.id)}" d="M${r.x},${r.y + 14} L${h.x},${h.y - 16}" marker-end="url(#arr-rule)"><title>${esc(r.name)} 推出 ${esc(h.label)}</title></path>`;
  }
  for (const n of g.nodes) {
    const w = nodeW(n);
    s += `<g class="node k-${esc(n.kind)}" data-id="${esc(n.id)}" transform="translate(${n.x - w / 2},${n.y - 15})"><rect class="sys-${esc(sysOf(n))}" width="${w}" height="30" rx="${n.kind === "abstract" ? 15 : 6}"/><text x="${w / 2}" y="19" text-anchor="middle">${esc(n.label)}</text><title>${esc(n.id)}</title></g>`;
  }
  if (layers.rule) for (const r of rules) {
    const w = nodeW(r);
    s += `<g class="node rule ${r.level === "DR" ? "dr" : ""}" data-rule="${esc(r.id)}" transform="translate(${r.x - w / 2},${r.y - 14})"><polygon points="${w / 2},0 ${w},14 ${w / 2},28 0,14"/><text x="${w / 2}" y="18" text-anchor="middle">${esc(r.label)}</text><title>${esc(r.nl)}</title></g>`;
  }
  svg.innerHTML = s;
  svg.querySelectorAll(".node[data-id]").forEach((el) => el.addEventListener("click", () => showConcept(el.dataset.id)));
  svg.querySelectorAll(".node[data-rule]").forEach((el) => el.addEventListener("click", () => showRule(el.dataset.rule)));
}
function highlight(ids, ruleIds) {
  document.querySelectorAll("#graph .node").forEach((el) => el.classList.toggle("selected", ids.has(el.dataset.id) || ruleIds.has(el.dataset.rule)));
  document.querySelectorAll("#graph .edge").forEach((el) => el.classList.toggle("hl", (ids.has(el.dataset.s) || ids.has(el.dataset.t)) && !el.dataset.rule || ruleIds.has(el.dataset.rule)));
  document.querySelectorAll("#concept-list button").forEach((b) => b.setAttribute("aria-pressed", ids.has(b.dataset.id) || ruleIds.has(b.dataset.rule)));
}
const lbl = (cid) => ontoData.nodes.find((x) => x.id === cid)?.label || cid;
const kindName = { abstract: "上位类", concrete: "业务对象", derived: "派生类" };
function showConcept(id) {
  const n = ontoData.nodes.find((x) => x.id === id); if (!n) return;
  const out = ontoData.edges.filter((e) => e.kind !== "subclass" && e.source === id);
  const inn = ontoData.edges.filter((e) => e.kind !== "subclass" && e.target === id && e.source !== id);
  const derivedBy = ontoData.rules.filter((r) => r.head === id), usedBy = ontoData.rules.filter((r) => r.uses.includes(id));
  highlight(new Set([id]), new Set([...derivedBy, ...usedBy].map((r) => r.id)));
  // 继承来的属性
  const ancestors = []; let cur = n; while (cur && cur.parents.length) { cur = ontoData.nodes.find((x) => x.id === cur.parents[0]); if (cur) ancestors.push(cur); }
  const inherited = ancestors.flatMap((a) => a.attributes.map((x) => ({ ...x, from: a.label })));
  $("#concept-detail").innerHTML = `<h2>${esc(n.label)} <span class="badge info">${kindName[n.kind]}</span> <span class="hint mono">alita:${esc(n.id)}</span></h2>
    <p class="hint">${esc(n.comment)}</p>
    <h3>层次</h3><ul class="path">
      ${n.parents.map((p) => `<li>是一种 <a href="#" data-goto="${esc(p)}">${esc(lbl(p))}</a></li>`).join("") || "<li>（顶层）</li>"}
      ${n.subclasses.length ? `<li>子类：${n.subclasses.map((c) => `<a href="#" data-goto="${esc(c)}">${esc(lbl(c))}</a>`).join("、")}</li>` : ""}
    </ul>
    <h3>关系</h3><ul class="path">
      ${out.map((e) => `<li>${esc(n.label)} —<b>${esc(e.label)}</b>→ <a href="#" data-goto="${esc(e.target)}">${esc(lbl(e.target))}</a> <span class="mono hint">${e.columns.map(esc).join(", ")}</span></li>`).join("")}
      ${inn.map((e) => `<li><a href="#" data-goto="${esc(e.source)}">${esc(lbl(e.source))}</a> —<b>${esc(e.label)}</b>→ ${esc(n.label)}${e.inverse_label ? ` <span class="hint">（反向：${esc(e.inverse_label)}）</span>` : ""}</li>`).join("")}
      ${!out.length && !inn.length ? "<li>（无直接关系）</li>" : ""}
    </ul>
    <h3>规则</h3><ul class="path">
      ${derivedBy.map((r) => `<li>由 <a href="#" data-rule-goto="${esc(r.id)}">◆ ${esc(r.name)}</a> 推出：${esc(r.nl)}</li>`).join("")}
      ${usedBy.map((r) => `<li>被 <a href="#" data-rule-goto="${esc(r.id)}">◆ ${esc(r.name)}</a> 使用 → 推出 ${esc(lbl(r.head))}</li>`).join("")}
      ${!derivedBy.length && !usedBy.length ? "<li>（无）</li>" : ""}
    </ul>
    <h3>属性（${n.attributes.length}${inherited.length ? `，另继承 ${inherited.length}` : ""}）</h3>
    ${n.attributes.length ? `<table><thead><tr><th>属性</th><th>别名（skos:altLabel）</th><th>映射字段（R2RML）</th></tr></thead><tbody>
    ${n.attributes.map((a) => `<tr><td>${esc(a.label)}<div class="hint mono">${esc(a.id)}</div></td><td>${esc(a.alt_labels.join("、") || "—")}</td><td class="mono">${a.columns.map(esc).join("<br>")}</td></tr>`).join("")}
    </tbody></table>` : `<p class="hint">${n.kind === "derived" ? "派生类没有自己的物理字段，实例由规则从父类实例中筛选出来，并继承父类的全部属性。" : "上位类不直接映射物理表，用于组织业务对象。"}</p>`}`;
  bindGoto();
}
function showRule(rid) {
  const r = ontoData.rules.find((x) => x.id === rid); if (!r) return;
  highlight(new Set([...r.uses, r.head]), new Set([rid]));
  $("#concept-detail").innerHTML = `<h2>◆ ${esc(r.name)} <span class="badge ${r.level === "FR" ? "ok" : "warn"}">${r.level === "FR" ? "事实规则" : "建议规则"}</span></h2>
    <p>${esc(r.nl)}</p>
    <h3>使用的对象</h3><ul class="path">${r.uses.map((u) => `<li><a href="#" data-goto="${esc(u)}">${esc(lbl(u))}</a></li>`).join("")}</ul>
    <h3>使用的属性 / 关系</h3><ul class="path">${Object.entries(r.predicate_labels).map(([k, v]) => `<li>${esc(v)} <span class="mono hint">alita:${esc(k)}</span></li>`).join("") || "<li>（只用到类）</li>"}</ul>
    <h3>推出</h3><p><a href="#" data-goto="${esc(r.head)}">${esc(lbl(r.head))}</a></p>
    <h3>SWRL（OntoWing 导出的 rules.ttl）</h3>${r.swrl ? `<pre class="code">${esc(r.swrl)}</pre>` : `<p class="hint">建议规则（DR）是给人看的结论，OntoWing 不把它导出为事实规则。</p>`}
    <h3>依据</h3><p class="hint">${esc(r.source)}</p>`;
  bindGoto();
}
function bindGoto() {
  $("#concept-detail").querySelectorAll("[data-goto]").forEach((a) => a.addEventListener("click", (e) => { e.preventDefault(); showConcept(a.dataset.goto); }));
  $("#concept-detail").querySelectorAll("[data-rule-goto]").forEach((a) => a.addEventListener("click", (e) => { e.preventDefault(); showRule(a.dataset.ruleGoto); }));
}
const ARTIFACTS = ["ontology.ttl", "mapping.r2rml.ttl", "rules.ttl", "wing_model.json", "wing_pipeline.json", "wing_rules.json", "build_report.json"];
function loadArtifactLinks() {
  $("#artifact-links").innerHTML = ARTIFACTS.map((a) => `<button type="button" data-a="${a}">${a}</button>`).join("") + '<span class="hint">（先在“构建”页执行一次构建才会落盘）</span>';
  $("#artifact-links").querySelectorAll("button").forEach((b) => b.addEventListener("click", async () => {
    try { const t = await (await fetch("/api/artifacts/" + b.dataset.a)).text(); $("#artifact-view").textContent = t.length > 200000 ? t.slice(0, 200000) + "\n…（已截断）" : t; }
    catch (e) { $("#artifact-view").textContent = e.message; }
  }));
}

// ------------------------------------------------------------------ 3 问答
let samples = null;
async function loadSamples() {
  if (samples) return;
  samples = await api("/api/samples");
  $("#sample-select").innerHTML += samples.map((s, i) => `<option value="${i}">[${esc(s.set)}] ${esc(s.id)} ${esc(s.from_dept)}：${esc(s.subject)}</option>`).join("");
}
$("#sample-select").addEventListener("change", (e) => {
  const s = samples[e.target.value]; if (!s) return;
  $("#sample-mail").textContent = `${s.from_dept}｜${s.subject}\n${s.body}`;
  $("#ocr-input").value = s.ocr; $("#fields-input").value = s.fields.join("、");
});
$("#ask-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  $("#ask-out").textContent = "查询中…";
  try { $("#ask-out").innerHTML = renderAsk(await api("/api/ask", { question: $("#ask-input").value })); }
  catch (err) { $("#ask-out").innerHTML = `<span class="badge bad">失败</span> ${esc(err.message)}`; }
});
function srcCell(s) {
  const o = s.ontology;
  return `<div class="src mono">${esc(s.system)}.${esc(s.table)}.${esc(s.field)}</div>
    <div class="hint">${esc(s.system_name)} ｜ 表：${esc(s.table_comment || "（无注释）")} ｜ 字段注释：${esc(s.field_comment || "（无注释）")}</div>
    ${o ? `<div class="hint">本体：${esc(o.concept_label)} / ${esc(o.label)} <span class="mono">${esc(o.predicate)}</span>${o.references ? ` → 引用 <span class="mono">${esc(o.references)}</span>` : ""}</div>` : ""}`;
}
function renderAsk(r) {
  if (r.status === "rule") return `<p>“${esc(r.concept_label)}”是由规则推导出来的业务分类，不是单个字段。推导链和用到的原表原字段：</p>
    <ol class="path">${r.chain.map((c) => `<li><b>${esc(c.rule)}</b>${c.level === "DR" ? ' <span class="badge warn">建议规则</span>' : ""}：${esc(c.nl)}
      ${c.uses_classes.length ? `<div class="hint">使用：${c.uses_classes.map(esc).join("、")} → 推出：${esc(c.head)}</div>` : ""}
      ${c.fields.length ? `<div class="mono hint">${c.fields.map((f) => `${esc(f.column)}（${esc(f.field_comment || f.ontology?.label || "")}）`).join("<br>")}</div>` : ""}
      ${c.swrl ? `<div class="mono hint">${esc(c.swrl)}</div>` : ""}</li>`).join("")}</ol>`;
  if (r.status === "derived_only") return `<p>“${esc(r.label)}”不是源表里的物理字段，而是中台计算出来的指标：</p><ul class="path">${r.derived_metrics.map((d) => `<li><span class="mono">${esc(d.platform_column)}</span>（${esc({ derived: "计算派生", aggregated: "汇总聚合" }[d.derivation] || d.derivation)}）← 源字段 <span class="mono">${d.sources.map(esc).join("、")}</span></li>`).join("")}</ul>`;
  if (r.status !== "ok") return `<p><span class="badge warn">未找到</span> 本体中没有与“${esc(r.label)}”匹配的属性。${r.near_misses.length ? "相近：" + r.near_misses.map((m) => esc(m.matched_name)).join("、") : ""}</p>`;
  let html = `<p>识别字段：<b>${esc(r.label)}</b></p><h3>原表原字段</h3><table><tbody>${r.answers.map((a) => `<tr><td>${srcCell(a)}</td><td><span class="badge ok">匹配“${esc(a.matched_name)}”</span></td></tr>`).join("")}</tbody></table>`;
  if (r.referenced_by.length) html += `<h3>同一标识在其他表的引用（外键）</h3><table><tbody>${r.referenced_by.map((a) => `<tr><td>${srcCell(a)}</td></tr>`).join("")}</tbody></table>`;
  if (r.derived_metrics.length) html += `<h3>中台同名派生指标</h3><ul class="path">${r.derived_metrics.map((d) => `<li class="mono">${esc(d.platform_column)}（${esc(d.derivation)}）← ${d.sources.map(esc).join(", ")}</li>`).join("")}</ul>`;
  return html;
}
$("#btn-trace").addEventListener("click", async (ev) => {
  const btn = ev.currentTarget; btn.disabled = true;
  const fields = $("#fields-input").value.split(/[、,，;；\s]+/).map((x) => x.trim()).filter(Boolean);
  $("#trace-out").textContent = "溯源中…";
  try { $("#trace-out").innerHTML = renderTrace(await api("/api/ask/screenshot", { ocr: $("#ocr-input").value, fields })); }
  catch (err) { $("#trace-out").innerHTML = `<span class="badge bad">失败</span> ${esc(err.message)}`; }
  btn.disabled = false;
});
function renderTrace(r) {
  const p = r.page;
  let html = `<h3>页面判定</h3><p>${esc(p.page_type)}${p.platform_table ? `：背后中台表 <span class="mono">${esc(p.platform_table)}</span>（${esc(p.platform_table_comment)}）` : "：字段直接取自源系统"}
    <span class="hint">中台表解释力 ${p.platform_table_score} ／ 源字段解释力 ${p.source_route_score}</span></p>`;
  html += `<table><thead><tr><th>截图字段</th><th>原表原字段</th><th>依据</th><th>置信度</th></tr></thead><tbody>`;
  for (const f of r.fields) {
    const ev = f.evidence || {};
    const status = f.status === "ok" ? `<span class="badge ok">${pct(f.confidence)}</span>` : `<span class="badge warn">待人工确认 ${pct(f.confidence)}</span>`;
    const why = [
      ev.matched_name ? `名称匹配“${esc(ev.matched_name)}”（${ev.name_score}）` : "",
      ev.value_ratio != null ? `截图值命中 ${pct(ev.value_ratio)}（${(ev.value_samples || []).map(esc).join("、")}）` : "截图值不足以校验",
      f.platform_column ? `中台列 <span class="mono">${esc(f.platform_column)}</span>，${esc({ direct: "直接搬运", derived: "计算派生", aggregated: "汇总聚合" }[f.derivation] || f.derivation)}` : "",
    ].filter(Boolean).join("<br>");
    const lineage = f.lineage.length ? `<details><summary>血缘路径（${f.lineage.length} 步）</summary><ol class="path">${f.lineage.map((s) => `<li class="mono">${esc(s.from)} → ${esc(s.to)} <span class="hint">${esc(s.kind)}${s.expr && s.expr !== s.from.split(".").pop() ? "：" + esc(s.expr) : ""}｜${s.provenance.map(provName).map(esc).join("、")}</span></li>`).join("")}</ol></details>` : "";
    const eq = f.equivalents.length ? `<details><summary>等价字段（${f.equivalents.length}）</summary><div class="mono hint">${f.equivalents.map(esc).join("<br>")}</div></details>` : "";
    html += `<tr><td><b>${esc(f.label)}</b><div class="hint">${(f.screenshot_values || []).map(esc).join("、")}</div></td>
      <td>${f.sources.map(srcCell).join("<hr>") || "—"}${eq}</td><td>${why}${lineage}</td><td>${status}</td></tr>`;
  }
  return html + "</tbody></table>";
}

refreshStatus();
