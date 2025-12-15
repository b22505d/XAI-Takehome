import React, { useEffect, useMemo, useState } from "react";

const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";
const STAGES = ["new", "contacted", "qualified", "meeting", "won", "lost"];

async function api(path, opts = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...(opts.headers || {}) },
    ...opts,
  });
  const txt = await res.text();
  let data = null;
  try { data = txt ? JSON.parse(txt) : null; } catch { data = { detail: txt }; }
  if (!res.ok) throw new Error(data?.detail || `HTTP ${res.status}`);
  return data;
}

function StagePill({ stage }) {
  const bg =
    stage === "won" ? "#D1FAE5" :
    stage === "lost" ? "#FEE2E2" :
    stage === "meeting" ? "#E0E7FF" :
    stage === "qualified" ? "#EDE9FE" :
    stage === "contacted" ? "#FEF3C7" :
    "#F3F4F6";
  return (
    <span style={{ padding: "3px 8px",color: "black", borderRadius: 999, background: bg, fontSize: 12, textTransform: "capitalize" }}>
      {stage}
    </span>
  );
}

export default function App() {
  const [view, setView] = useState("pipeline"); // table | pipeline
  const [q, setQ] = useState("");
  const [stageFilter, setStageFilter] = useState("");
  const [leads, setLeads] = useState([]);
  const [cfg, setCfg] = useState({ criteria: [], updated_at: null });
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");

  const [form, setForm] = useState({ name: "", company: "", role: "", industry: "", notes: "" });

  const [historyOpen, setHistoryOpen] = useState(false);
  const [historyLead, setHistoryLead] = useState(null);
  const [history, setHistory] = useState([]);
  const [evalResult, setEvalResult] = useState(null);

  async function loadAll() {
    setErr("");
    setLoading(true);
    try {
      const [cfgData, leadsData] = await Promise.all([
        api("/scoring-config"),
        api(`/leads?q=${encodeURIComponent(q)}&stage=${encodeURIComponent(stageFilter)}`),
      ]);
      setCfg(cfgData);
      setLeads(leadsData);
    } catch (e) {
      setErr(String(e.message || e));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { loadAll(); }, []); // initial
  useEffect(() => {
    const t = setTimeout(loadAll, 250);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [q, stageFilter]);

  async function createLead(e) {
    e.preventDefault();
    setErr("");
    try {
      await api("/leads", { method: "POST", body: JSON.stringify(form) });
      setForm({ name: "", company: "", role: "", industry: "", notes: "" });
      await loadAll();
    } catch (e2) {
      setErr(String(e2.message || e2));
    }
  }

  async function scoreLead(id) {
    setErr("");
    try {
      await api(`/leads/${id}/score`, { method: "POST" });
      await loadAll();
    } catch (e) {
      setErr(String(e.message || e));
    }
  }
  async function runEvaluation() {
    setErr("");
    try {
      const out = await api("/eval/run", { method: "POST" });
      setEvalResult(out);
    } catch (e) {
      setErr(String(e.message || e));
    }
  }
  
  async function msgLead(id) {
    setErr("");
    try {
      const out = await api(`/leads/${id}/message`, { method: "POST" });
      // quick visible output
      alert(out.message);
      await loadAll();
    } catch (e) {
      setErr(String(e.message || e));
    }
  }

  async function delLead(id) {
    setErr("");
    try {
      await api(`/leads/${id}`, { method: "DELETE" });
      await loadAll();
    } catch (e) {
      setErr(String(e.message || e));
    }
  }

  async function openHistory(lead) {
    setErr("");
    try {
      const acts = await api(`/leads/${lead.id}/activities`);
      setHistoryLead(lead);
      setHistory(acts);
      setHistoryOpen(true);
    } catch (e) {
      setErr(String(e.message || e));
    }
  }

  async function saveConfig() {
    setErr("");
    try {
      await api("/scoring-config", { method: "PUT", body: JSON.stringify({ criteria: cfg.criteria }) });
      await loadAll();
    } catch (e) {
      setErr(String(e.message || e));
    }
  }

  async function rescoreAll() {
    setErr("");
    try {
      await api("/leads/rescore-all", { method: "POST" });
      await loadAll();
    } catch (e) {
      setErr(String(e.message || e));
    }
  }

  const pipeline = useMemo(() => {
    const by = {};
    for (const s of STAGES) by[s] = [];
    for (const l of leads) by[l.stage]?.push(l);
    return by;
  }, [leads]);

  function updateCriterion(i, key, val) {
    const next = structuredClone(cfg);
    next.criteria[i][key] = val;
    setCfg(next);
  }

  function addCriterion() {
    setCfg({
      ...cfg,
      criteria: [...(cfg.criteria || []), { name: "New criterion", weight: 10, description: "" }],
    });
  }

  function removeCriterion(i) {
    const next = structuredClone(cfg);
    next.criteria.splice(i, 1);
    setCfg(next);
  }

  return (
    <div style={{ fontFamily: "system-ui, -apple-system, Segoe UI, Roboto", padding: 16, maxWidth: 1200, margin: "0 auto" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 10 }}>
        <h2 style={{ margin: 0 }}>Lead Qualifier <button onClick={runEvaluation}>Run evaluation</button>
        </h2>
        
        <button onClick={() => setView("pipeline")} disabled={view === "pipeline"}>Pipeline</button>
        <button onClick={() => setView("table")} disabled={view === "table"}>Table</button>
        <div style={{ marginLeft: "auto", display: "flex", gap: 8 }}>
        {evalResult ? (
  <div style={{ border: "1px solid #E5E7EB", borderRadius: 12, padding: 12, marginBottom: 12 }}>
    <h3 style={{ marginTop: 0 }}>Evaluation</h3>
    <pre style={{ whiteSpace: "pre-wrap", margin: 0 }}>{JSON.stringify(evalResult, null, 2)}</pre>
  </div>
) : null}
          <input
            placeholder="Search…"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            style={{ padding: 8, width: 260 }}
          />
          <select value={stageFilter} onChange={(e) => setStageFilter(e.target.value)} style={{ padding: 8 }}>
            <option value="">All stages</option>
            {STAGES.map((s) => <option key={s} value={s}>{s}</option>)}
          </select>
          <button onClick={loadAll} disabled={loading}>Refresh</button>
        </div>
      </div>

      {err ? (
        <div style={{ padding: 10, borderRadius: 8, marginBottom: 10, whiteSpace: "pre-wrap" }}>
          {err}
        </div>
      ) : null}

      {/* Scoring config */}
      <div style={{ border: "1px solid #E5E7EB", borderRadius: 12, padding: 12, marginBottom: 12 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 8 }}>
          <h3 style={{ margin: 0 }}>Scoring criteria (user-defined)</h3>
          <button onClick={addCriterion}>+ Add</button>
          <button onClick={saveConfig}>Save</button>
          <button onClick={rescoreAll}>Re-score all</button>
          <div style={{ marginLeft: "auto", fontSize: 12, color: "#6B7280" }}>
            Updated: {cfg.updated_at ? new Date(cfg.updated_at).toLocaleString() : "—"}
          </div>
        </div>

        <div style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr style={{ textAlign: "left" }}>
                <th style={{ borderBottom: "1px solid #E5E7EB", padding: 8 }}>Name</th>
                <th style={{ borderBottom: "1px solid #E5E7EB", padding: 8, width: 90 }}>Weight</th>
                <th style={{ borderBottom: "1px solid #E5E7EB", padding: 8 }}>Description</th>
                <th style={{ borderBottom: "1px solid #E5E7EB", padding: 8, width: 80 }}> </th>
              </tr>
            </thead>
            <tbody>
              {(cfg.criteria || []).map((c, i) => (
                <tr key={i}>
                  <td style={{ padding: 8 }}>
                    <input value={c.name} onChange={(e) => updateCriterion(i, "name", e.target.value)} style={{ width: "100%", padding: 6 }} />
                  </td>
                  <td style={{ padding: 8 }}>
                    <input
                      type="number"
                      min={0}
                      max={100}
                      value={c.weight}
                      onChange={(e) => updateCriterion(i, "weight", Number(e.target.value))}
                      style={{ width: 70, padding: 6 }}
                    />
                  </td>
                  <td style={{ padding: 8 }}>
                    <input value={c.description} onChange={(e) => updateCriterion(i, "description", e.target.value)} style={{ width: "100%", padding: 6 }} />
                  </td>
                  <td style={{ padding: 8 }}>
                    <button onClick={() => removeCriterion(i)}>Remove</button>
                  </td>
                </tr>
              ))}
              {!cfg.criteria?.length ? (
                <tr><td colSpan={4} style={{ padding: 8, color: "#6B7280" }}>No criteria yet</td></tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </div>

      {/* Create lead */}
      <div style={{ display: "grid", gridTemplateColumns: "360px 1fr", gap: 12 }}>
        <div style={{ border: "1px solid #E5E7EB", borderRadius: 12, padding: 12 }}>
          <h3 style={{ marginTop: 0 }}>Add lead</h3>
          <form onSubmit={createLead} style={{ display: "grid", gap: 8 }}>
            <input placeholder="Name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required style={{ padding: 8 }} />
            <input placeholder="Company" value={form.company} onChange={(e) => setForm({ ...form, company: e.target.value })} required style={{ padding: 8 }} />
            <input placeholder="Role" value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })} style={{ padding: 8 }} />
            <input placeholder="Industry" value={form.industry} onChange={(e) => setForm({ ...form, industry: e.target.value })} style={{ padding: 8 }} />
            <textarea placeholder="Notes" value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} rows={4} style={{ padding: 8 }} />
            <button type="submit">Create</button>
          </form>
        </div>

        {/* Leads */}
        <div style={{ border: "1px solid #E5E7EB", borderRadius: 12, padding: 12 }}>
          {view === "table" ? (
            <>
              <h3 style={{ marginTop: 0 }}>Leads</h3>
              <div style={{ overflowX: "auto" }}>
                <table style={{ width: "100%", borderCollapse: "collapse" }}>
                  <thead>
                    <tr style={{ textAlign: "left" }}>
                      <th style={{ borderBottom: "1px solid #E5E7EB", padding: 8 }}>Lead</th>
                      <th style={{ borderBottom: "1px solid #E5E7EB", padding: 8 }}>Stage</th>
                      <th style={{ borderBottom: "1px solid #E5E7EB", padding: 8 }}>Score</th>
                      <th style={{ borderBottom: "1px solid #E5E7EB", padding: 8 }}>Updated</th>
                      <th style={{ borderBottom: "1px solid #E5E7EB", padding: 8 }}>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {leads.map((l) => (
                      <tr key={l.id}>
                        <td style={{ padding: 8 }}>
                          <div style={{ fontWeight: 600 }}>{l.name} — {l.company}</div>
                          <div style={{ fontSize: 12, color: "#6B7280" }}>{l.role || "—"} · {l.industry || "—"}</div>
                        </td>
                        <td style={{ padding: 8 }}><StagePill stage={l.stage} /></td>
                        <td style={{ padding: 8 }}>{l.score ?? "—"}</td>
                        <td style={{ padding: 8, fontSize: 12, color: "#6B7280" }}>{new Date(l.updated_at).toLocaleString()}</td>
                        <td style={{ padding: 8 }}>
                          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                            <button onClick={() => scoreLead(l.id)}>Score</button>
                            <button onClick={() => msgLead(l.id)}>Message</button>
                            <button onClick={() => openHistory(l)}>History</button>
                            <button onClick={() => delLead(l.id)}>Delete</button>
                          </div>
                        </td>
                      </tr>
                    ))}
                    {!leads.length ? (
                      <tr><td colSpan={5} style={{ padding: 8, color: "#6B7280" }}>No leads</td></tr>
                    ) : null}
                  </tbody>
                </table>
              </div>
            </>
          ) : (
            <>
              <div style={{ display: "flex", alignItems: "center" }}>
                <h3 style={{ marginTop: 0, marginBottom: 10 }}>Pipeline</h3>
                <div style={{ marginLeft: "auto", display: "flex", gap: 8 }}>
                  <button onClick={rescoreAll}>Re-score all</button>
                </div>
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "repeat(6, 1fr)", gap: 10 }}>
                {STAGES.map((s) => (
                  <div key={s} style={{ border: "1px solid #E5E7EB", borderRadius: 12, padding: 10, minHeight: 220 }}>
                    <div style={{ display: "flex", alignItems: "center", marginBottom: 8 }}>
                      <div style={{ fontWeight: 700, textTransform: "capitalize" }}>{s}</div>
                      <div style={{ marginLeft: "auto", fontSize: 12, color: "#6B7280" }}>{pipeline[s]?.length || 0}</div>
                    </div>

                    <div style={{ display: "grid", gap: 8 }}>
                      {(pipeline[s] || []).map((l) => (
                        <div key={l.id} style={{ border: "1px solid #E5E7EB", borderRadius: 12, padding: 8 }}>
                          <div style={{ fontWeight: 700 }}>{l.company}</div>
                          <div style={{ fontSize: 12, color: "#6B7280" }}>{l.name}{l.role ? ` · ${l.role}` : ""}</div>
                          <div style={{ marginTop: 6, display: "flex", alignItems: "center", gap: 8 }}>
                            <StagePill stage={l.stage} />
                            <div style={{ fontSize: 12 }}>Score: <b>{l.score ?? "—"}</b></div>
                          </div>
                          {l.last_message ? (
                            <div style={{ marginTop: 6, fontSize: 12, color: "#374151", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                              Msg: {l.last_message}
                            </div>
                          ) : null}
                          <div style={{ marginTop: 8, display: "flex", gap: 8, flexWrap: "wrap" }}>
                            <button onClick={() => scoreLead(l.id)}>Score</button>
                            <button onClick={() => msgLead(l.id)}>Message</button>
                            <button onClick={() => openHistory(l)}>History</button>
                          </div>
                        </div>
                      ))}
                      {!(pipeline[s] || []).length ? (
                        <div style={{ fontSize: 12, color: "#9CA3AF" }}>—</div>
                      ) : null}
                    </div>
                  </div>
                ))}
              </div>
            </>
          )}
        </div>
      </div>

      {/* History modal */}
      {historyOpen ? (
        <div
          onClick={() => setHistoryOpen(false)}
          style={{
            position: "fixed", inset: 0, background: "rgba(0,0,0,0.35)",
            display: "flex", alignItems: "center", justifyContent: "center", padding: 20
          }}
        >
          <div onClick={(e) => e.stopPropagation()} style={{ borderRadius: 12, width: 820, maxWidth: "95vw", padding: 14 }}>
            <div style={{ display: "flex", alignItems: "center" }}>
              <h3 style={{ margin: 0 }}>
                Activity — {historyLead?.name} @ {historyLead?.company}
              </h3>
              <button style={{ marginLeft: "auto" }} onClick={() => setHistoryOpen(false)}>Close</button>
            </div>

            <div style={{ marginTop: 10, maxHeight: 420, overflow: "auto", border: "1px solid #E5E7EB", borderRadius: 12 }}>
              {history.map((a) => (
                <div key={a.id} style={{ padding: 10, borderBottom: "1px solid #E5E7EB" }}>
                  <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
                    <b style={{ textTransform: "uppercase", fontSize: 12 }}>{a.type}</b>
                    <span style={{ fontSize: 12, color: "#6B7280" }}>{new Date(a.created_at).toLocaleString()}</span>
                  </div>
                  <div style={{ marginTop: 6, fontSize: 13, whiteSpace: "pre-wrap" }}>{a.detail}</div>
                </div>
              ))}
              {!history.length ? <div style={{ padding: 10, color: "#6B7280" }}>No activity</div> : null}
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
