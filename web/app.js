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
    ${metric(s.concepts, "概念（类）")}${metric(s.attributes, "属性")}${metric(s.relations, "关系")}
    ${metric(s.bindings, "数据管道绑定")}${metric(s.tables_in_scope, "纳入的源表")}${metric(s.tables_excluded.length, "剔除的噪声表")}</div>
    <p class="hint">元数据来源：${esc(s.metadata_source === "mysql" ? "MySQL information_schema" : "DDL 文件")}；OntoWing ${esc(r.ontowing.commit)}${r.ontowing.backend ? `（${esc(r.ontowing.backend)}）` : ""}</p></div>`;
  const wv = r.wing_validation;
  html += `<div class="card"><h2>OntoWing 静态校验</h2><table><thead><tr><th>对象</th><th>结果</th><th>检查项</th><th>诊断</th></tr></thead><tbody>
    ${["model", "pipeline"].map((k) => `<tr><td>${k === "model" ? "本体（wing-model-editor/1）" : "数据管道映射（wing-pipeline-editor/2）"}</td>
    <td>${wv[k].valid ? '<span class="badge ok">有效</span>' : '<span class="badge bad">无效</span>'}</td>
    <td class="mono">${esc(JSON.stringify(wv[k].checks || {}))}</td><td>${wv[k].diagnostics.length ? esc(wv[k].diagnostics.map((d) => d.code).join("、")) : "无"}</td></tr>`).join("")}
    </tbody></table></div>`;
  if (r.r2rml_execution && r.r2rml_execution.ran) {
    const x = r.r2rml_execution;
    html += `<div class="card"><h2>R2RML 实跑（Morph-KGC，沙箱数据）</h2>
      <p>${x.passed ? '<span class="badge ok">通过</span>' : '<span class="badge bad">未通过</span>'} 生成三元组 ${x.triples.toLocaleString()} 个；空概念 ${x.empty_concepts.length} 个；悬空引用 ${x.dangling_total} 个${x.errors.length ? "；错误：" + esc(x.errors.join("；")) : ""}</p>
      <table><thead><tr><th>概念</th><th>实例数</th></tr></thead><tbody>${Object.entries(x.instances_by_concept).map(([k, v]) => `<tr><td>${esc(k)}</td><td>${v.toLocaleString()}</td></tr>`).join("")}</tbody></table></div>`;
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
let ontoLoaded = false, ontoData = null;
async function loadOntology() {
  if (ontoLoaded) return;
  $("#concept-detail").innerHTML = '<p class="hint">加载中…（首次会在后台构建本体）</p>';
  try {
    ontoData = await api("/api/ontology");
    ontoLoaded = true;
    drawGraph(ontoData);
    $("#concept-list").innerHTML = ontoData.nodes.map((n) => `<li><button type="button" data-id="${esc(n.id)}" aria-pressed="false">${esc(n.label)}</button></li>`).join("");
    $("#concept-list").querySelectorAll("button").forEach((b) => b.addEventListener("click", () => showConcept(b.dataset.id)));
    showConcept(ontoData.nodes.find((n) => n.id === "Consumer")?.id || ontoData.nodes[0].id);
    loadArtifactLinks();
  } catch (e) { $("#concept-detail").innerHTML = `<span class="badge bad">失败</span> ${esc(e.message)}`; }
}
function sysOf(n) { const t = n.tables[0] || ""; return t.split(".")[0]; }
function layout(nodes, edges, W, H) {
  // 按系统分三列初始化，再做少量力导向迭代，结果确定（不使用随机数）
  const cols = { yx186: 0, cjxt: 1, kf95598: 2 };
  const groups = {};
  nodes.forEach((n) => { const g = cols[sysOf(n)] ?? 0; (groups[g] = groups[g] || []).push(n); });
  for (const [g, list] of Object.entries(groups)) {
    const cx = [W * 0.3, W * 0.72, W * 0.78][g];
    list.forEach((n, i) => {
      const ang = (i / list.length) * Math.PI * 2;
      const r = g === "0" ? Math.min(W, H) * 0.3 : Math.min(W, H) * 0.18;
      n.x = cx + r * Math.cos(ang); n.y = (g === "2" ? H * 0.8 : g === "1" ? H * 0.32 : H * 0.5) + r * Math.sin(ang);
    });
  }
  const byId = Object.fromEntries(nodes.map((n) => [n.id, n]));
  for (let it = 0; it < 250; it++) {
    for (const a of nodes) for (const b of nodes) {
      if (a === b) continue;
      const dx = a.x - b.x, dy = a.y - b.y, d2 = Math.max(dx * dx + dy * dy, 100);
      const f = 9000 / d2; a.x += (dx / Math.sqrt(d2)) * f * 0.05; a.y += (dy / Math.sqrt(d2)) * f * 0.05;
    }
    for (const e of edges) {
      const s = byId[e.source], t = byId[e.target]; if (!s || !t || s === t) continue;
      const dx = t.x - s.x, dy = t.y - s.y, d = Math.sqrt(dx * dx + dy * dy) || 1, k = (d - 150) * 0.01;
      s.x += dx / d * k; s.y += dy / d * k; t.x -= dx / d * k; t.y -= dy / d * k;
    }
    for (const n of nodes) { n.x = Math.min(W - 70, Math.max(70, n.x)); n.y = Math.min(H - 25, Math.max(25, n.y)); }
  }
  // 按节点实际宽高做碰撞消解，避免标签重叠
  const wOf = (n) => Math.max(80, n.label.length * 13 + 18);
  for (let it = 0; it < 120; it++) {
    let moved = false;
    for (let i = 0; i < nodes.length; i++) for (let j = i + 1; j < nodes.length; j++) {
      const a = nodes[i], b = nodes[j];
      const ox = (wOf(a) + wOf(b)) / 2 + 12 - Math.abs(a.x - b.x), oy = 30 + 14 - Math.abs(a.y - b.y);
      if (ox > 0 && oy > 0) {
        moved = true;
        if (oy < ox) { const s = (a.y <= b.y ? -1 : 1) * oy / 2; a.y += s; b.y -= s; }
        else { const s = (a.x <= b.x ? -1 : 1) * ox / 2; a.x += s; b.x -= s; }
      }
    }
    for (const n of nodes) { n.x = Math.min(W - wOf(n) / 2 - 4, Math.max(wOf(n) / 2 + 4, n.x)); n.y = Math.min(H - 20, Math.max(20, n.y)); }
    if (!moved) break;
  }
}
function drawGraph(g) {
  const svg = $("#graph"); const W = svg.clientWidth || 800, H = svg.clientHeight || 560;
  svg.setAttribute("viewBox", `0 0 ${W} ${H}`);
  layout(g.nodes, g.edges, W, H);
  const byId = Object.fromEntries(g.nodes.map((n) => [n.id, n]));
  let s = '<defs><marker id="arr" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#9aa4b4"/></marker></defs>';
  for (const e of g.edges) {
    const a = byId[e.source], b = byId[e.target]; if (!a || !b) continue;
    if (a === b) { s += `<path class="edge" data-s="${esc(a.id)}" data-t="${esc(b.id)}" d="M${a.x + 40},${a.y - 12} C${a.x + 90},${a.y - 60} ${a.x - 90},${a.y - 60} ${a.x - 40},${a.y - 12}" marker-end="url(#arr)"/>`; continue; }
    const dx = b.x - a.x, dy = b.y - a.y, d = Math.sqrt(dx * dx + dy * dy) || 1;
    const ex = b.x - dx / d * 55, ey = b.y - dy / d * 18;
    s += `<line class="edge" data-s="${esc(a.id)}" data-t="${esc(b.id)}" x1="${a.x}" y1="${a.y}" x2="${ex}" y2="${ey}" marker-end="url(#arr)"><title>${esc(e.label)}</title></line>`;
  }
  for (const n of g.nodes) {
    const w = Math.max(80, n.label.length * 13 + 18);
    s += `<g class="node" data-id="${esc(n.id)}" transform="translate(${n.x - w / 2},${n.y - 15})"><rect class="sys-${esc(sysOf(n))}" width="${w}" height="30" rx="6"/><text x="${w / 2}" y="19" text-anchor="middle">${esc(n.label)}</text><title>${esc(n.id)}：${n.attributes.length} 个属性</title></g>`;
  }
  svg.innerHTML = s;
  svg.querySelectorAll(".node").forEach((el) => el.addEventListener("click", () => showConcept(el.dataset.id)));
}
function showConcept(id) {
  const n = ontoData.nodes.find((x) => x.id === id); if (!n) return;
  document.querySelectorAll("#graph .node").forEach((el) => el.classList.toggle("selected", el.dataset.id === id));
  document.querySelectorAll("#graph .edge").forEach((el) => el.classList.toggle("hl", el.dataset.s === id || el.dataset.t === id));
  document.querySelectorAll("#concept-list button").forEach((b) => b.setAttribute("aria-pressed", b.dataset.id === id));
  const label = (cid) => ontoData.nodes.find((x) => x.id === cid)?.label || cid;
  const out = ontoData.edges.filter((e) => e.source === id), inn = ontoData.edges.filter((e) => e.target === id && e.source !== id);
  $("#concept-detail").innerHTML = `<h2>${esc(n.label)} <span class="hint mono">alita:${esc(n.id)}</span></h2>
    <p class="hint">${esc(n.description)}</p>
    <h3>属性（${n.attributes.length}）</h3>
    <table><thead><tr><th>属性</th><th>别名（skos:altLabel）</th><th>映射字段（R2RML）</th></tr></thead><tbody>
    ${n.attributes.map((a) => `<tr><td>${esc(a.label)}<div class="hint mono">${esc(a.id)}</div></td><td>${esc(a.alt_labels.join("、") || "—")}</td><td class="mono">${a.columns.map(esc).join("<br>")}</td></tr>`).join("")}
    </tbody></table>
    <h3>关系</h3><ul class="path">
    ${out.map((e) => `<li>→ ${esc(label(e.target))}：${esc(e.label)} <span class="mono hint">${e.columns.map(esc).join(", ")}</span></li>`).join("")}
    ${inn.map((e) => `<li>← ${esc(label(e.source))}：${esc(e.label)}</li>`).join("") || ""}
    </ul>`;
}
const ARTIFACTS = ["ontology.ttl", "mapping.r2rml.ttl", "wing_model.json", "wing_pipeline.json", "build_report.json"];
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
