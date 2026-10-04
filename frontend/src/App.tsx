import { number } from "./format";
import React, { useEffect, useState } from "react";
import {
  Inbox,
  Activity,
  BarChart3,
  Settings as SettingsIcon,
  ShieldCheck,
  ArrowUpRight,
  Search,
  SlidersHorizontal,
  Bell,
  LockKeyhole,
  CircleDot,
  ChevronRight,
  Check,
  Cpu,
  Zap,
} from "lucide-react";
import "./style.css";

type Settings = {
  model: string;
  threshold: number;
  polling_interval: number;
  pipeline: "two_stage" | "baseline_llm";
  context_messages: number;
  notifications: boolean;
  notification_previews: boolean;
};
type Verdict = {
  important: boolean;
  importance_score: number;
  category: string;
  reason: string;
  model: string;
  latency_ms: number;
  requires_response: boolean;
};
type Message = {
  id: string;
  sender_display_name: string;
  timestamp: string;
  text: string;
  source: string;
  status: string;
  classification: Verdict | null;
  label: { important: boolean; category: string } | null;
};
type Status = {
  health: string;
  fixture: boolean;
  source: string;
  persistent: boolean;
  source_error: string | null;
  notification_error: string | null;
};
type Metrics = Record<string, number | null>;
const pages = ["Important inbox", "Activity", "Analytics", "Settings"] as const;
type Page = (typeof pages)[number];
const icons = [Inbox, Activity, BarChart3, SettingsIcon];
async function api<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`/api/${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      "X-PriorInbox": "local",
      ...options?.headers,
    },
  });
  if (!response.ok)
    throw new Error(`Request failed (${response.status}). Please try again.`);
  return response.json() as Promise<T>;
}
function App() {
  const [page, setPage] = useState<Page>("Important inbox");
  const [messages, setMessages] = useState<Message[]>([]);
  const [total, setTotal] = useState(0);
  const [metrics, setMetrics] = useState<Metrics>({});
  const [status, setStatus] = useState<Status | null>(null);
  const [settings, setSettings] = useState<Settings | null>(null);
  const [models, setModels] = useState<string[]>([]);
  const [error, setError] = useState("");
  const [saved, setSaved] = useState("");
  const [saving, setSaving] = useState(false);
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState("all");
  const [selected, setSelected] = useState<Message | null>(null);
  useEffect(() => {
    let active = true;
    async function refresh() {
      try {
        const [rows, m, s] = await Promise.all([
          api<{ items: Message[]; total: number }>("messages?limit=500"),
          api<Metrics>("analytics"),
          api<Status>("status"),
        ]);
        if (active) {
          setMessages(rows.items);
          setTotal(rows.total);
          setMetrics(m);
          setStatus(s);
          setError("");
        }
      } catch (e) {
        if (active) setError((e as Error).message);
      }
    }
    void refresh();
    const timer = setInterval(() => void refresh(), 3000);
    void api<Settings>("settings")
      .then((s) => {
        if (active) setSettings(s);
      })
      .catch((e) => {
        if (active) setError(e.message);
      });
    void api<{ models: string[] }>("models")
      .then((r) => {
        if (active) setModels(r.models);
      })
      .catch(() => {});
    return () => {
      active = false;
      clearInterval(timer);
    };
  }, []);
  useEffect(() => {
    if (!selected) return;
    const previous = document.activeElement as HTMLElement | null;
    const dialog = document.querySelector<HTMLElement>('[role="dialog"]');
    const buttons = Array.from(
      dialog?.querySelectorAll<HTMLButtonElement>("button") ?? [],
    );
    buttons[0]?.focus();
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") setSelected(null);
      if (event.key === "Tab" && buttons.length) {
        const first = buttons[0],
          last = buttons[buttons.length - 1];
        if (event.shiftKey && document.activeElement === first) {
          event.preventDefault();
          last.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
          event.preventDefault();
          first.focus();
        }
      }
    };
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("keydown", onKey);
      previous?.focus();
    };
  }, [selected?.id]);
  const important = messages.filter((m) => m.classification?.important);
  const shown = (page === "Important inbox" ? important : messages).filter(
    (m) =>
      `${m.sender_display_name} ${m.text}`
        .toLowerCase()
        .includes(query.toLowerCase()) &&
      (category === "all" || m.classification?.category === category),
  );
  const categories = [
    ...new Set(
      messages.flatMap((m) =>
        m.classification ? [m.classification.category] : [],
      ),
    ),
  ];
  const navigate = (p: Page) => {
    setPage(p);
    setQuery("");
    setCategory("all");
    setSelected(null);
  };
  async function save() {
    if (!settings) return;
    setSaving(true);
    setSaved("");
    try {
      await api("settings", { method: "PUT", body: JSON.stringify(settings) });
      setSaved("Settings saved. New messages will use these preferences.");
    } catch (e) {
      setSaved((e as Error).message);
    } finally {
      setSaving(false);
    }
  }
  async function label(important: boolean) {
    if (!selected?.classification) return;
    try {
      await api(`messages/${selected.id}/label`, {
        method: "PUT",
        body: JSON.stringify({
          important,
          category: selected.classification.category,
        }),
      });
      setSelected({
        ...selected,
        label: { important, category: selected.classification.category },
      });
    } catch (e) {
      setError((e as Error).message);
    }
  }
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <a
          className="brand"
          href="#"
          onClick={(e) => {
            e.preventDefault();
            navigate("Important inbox");
          }}
        >
          <span className="brand-mark">
            <Inbox size={22} />
          </span>
          PriorInbox<span className="brand-dot">.</span>
        </a>
        <div className="workspace">
          <span className="workspace-avatar">P</span>
          <div>
            Personal workspace<small>LOCAL ENVIRONMENT</small>
          </div>
          <LockKeyhole size={13} />
        </div>
        <span className="nav-caption">WORKSPACE</span>
        <nav>
          {pages.map((p, i) => {
            const Icon = icons[i];
            return (
              <button
                key={p}
                className={page === p ? "nav-item active" : "nav-item"}
                onClick={() => navigate(p)}
              >
                <Icon size={18} />
                {p}
                {p === "Important inbox" && (
                  <span className="count">{metrics.important ?? 0}</span>
                )}
              </button>
            );
          })}
        </nav>
        <div className="sidebar-bottom">
          <div className="privacy-card">
            <ShieldCheck size={22} />
            <strong>Your messages stay yours.</strong>
            <p>
              Classified on your machine.
              <br />
              No cloud AI. Your device, your control.
            </p>
            <span>
              <span className="dot" /> Local inference only
            </span>
          </div>
          <div className="version">
            <span className="mini-logo">P</span>PriorInbox <small>v0.1.0</small>
          </div>
        </div>
      </aside>
      <div className="main-shell">
        <header className="topbar">
          <div>
            Workspace <ChevronRight size={14} /> <strong>{page}</strong>
          </div>
          <span className="local-pill">
            <span className="dot" /> Running locally <LockKeyhole size={12} />
          </span>
        </header>
        <main>
          <div className="page-heading">
            <div className="eyebrow">LESS NOISE. MORE SIGNAL.</div>
            <div className="heading-row">
              <div>
                <h1>
                  {page === "Important inbox"
                    ? "Your attention, protected."
                    : page}
                </h1>
                <p>
                  {page === "Important inbox"
                    ? "The messages that matter, without everything else."
                    : page === "Activity"
                      ? "A transparent view of every classification."
                      : page === "Analytics"
                        ? "Measured performance. Nothing made up."
                        : "Make room for what matters to you."}
                </p>
              </div>
              <button
                className="secondary"
                onClick={() =>
                  navigate(page === "Settings" ? "Important inbox" : "Settings")
                }
              >
                <SlidersHorizontal size={15} />
                {page === "Settings" ? "Back to inbox" : "Tune your filter"}
              </button>
            </div>
          </div>
          {error && (
            <div className="alert" role="alert">
              {error} Check that the backend is running.
            </div>
          )}
          {status?.source_error && (
            <div className="alert" role="alert">
              {status.source_error}
            </div>
          )}
          {status?.notification_error && (
            <div className="alert">{status.notification_error}</div>
          )}
          {status && (
            <div
              className={status.fixture ? "mode-banner" : "mode-banner live"}
            >
              <Cpu size={16} />
              <span>
                {status.fixture ? "Fixture demo" : "Local AI"}
                <b>·</b>
                {status.fixture
                  ? "Synthetic messages and simulated verdicts. Metrics are for demonstration only."
                  : status.health}
              </span>
              <span className="mode-tag">{status.source.toUpperCase()}</span>
            </div>
          )}
          {page !== "Settings" && (
            <section className="stats-grid" aria-label="Inbox statistics">
              <Stat
                title="Messages processed"
                value={number(metrics.messages_processed)}
                note="Across your local inbox"
                icon={<Inbox size={17} />}
              />
              <Stat
                title="Worth your attention"
                value={number(metrics.important)}
                note="Actionable messages surfaced"
                icon={<CircleDot size={17} />}
                accent
              />
              <Stat
                title="Noise filtered out"
                value={number(metrics.notification_reduction_pct, "%")}
                note={`${number(metrics.notifications_suppressed)} notifications suppressed`}
                icon={<ShieldCheck size={17} />}
              />
              <Stat
                title="Median classification"
                value={number(metrics.p50_latency_ms, " ms")}
                note={
                  status?.fixture
                    ? "Fixture timing · not model latency"
                    : `${number(metrics.ollama_invocation_pct, "%")} sent to Ollama`
                }
                icon={<Zap size={17} />}
              />
            </section>
          )}
          {(page === "Important inbox" || page === "Activity") && (
            <section className="inbox-panel">
              <div className="panel-header">
                <div>
                  <h2>
                    {page === "Important inbox"
                      ? "Important inbox"
                      : "Recent activity"}{" "}
                    <span className="soft-count">
                      {page === "Important inbox"
                        ? important.length
                        : messages.length}
                    </span>
                  </h2>
                  <p>
                    {page === "Important inbox"
                      ? "A little less scrolling. A lot more focus."
                      : `Showing the latest ${messages.length} of ${total} received messages.`}
                  </p>
                </div>
                <span className="updating">
                  <span className="dot" /> Updates automatically
                </span>
              </div>
              <div className="toolbar">
                <label className="search">
                  <Search size={16} />
                  <input
                    aria-label="Search messages"
                    placeholder="Search messages or people…"
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                  />
                </label>
                <select
                  aria-label="Filter category"
                  value={category}
                  onChange={(e) => setCategory(e.target.value)}
                >
                  <option value="all">All categories</option>
                  {categories.map((c) => (
                    <option key={c} value={c}>
                      {c.replaceAll("_", " ")}
                    </option>
                  ))}
                </select>
              </div>
              <div className="list-label">
                <span>MESSAGE</span>
                <span>CLASSIFICATION</span>
              </div>
              <div className="message-list">
                {shown.map((m, i) => (
                  <button
                    key={m.id}
                    className="message-row"
                    onClick={() => setSelected(m)}
                  >
                    <span className={`avatar color-${i % 5}`}>
                      {m.sender_display_name
                        .split(" ")
                        .map((s) => s[0])
                        .slice(0, 2)
                        .join("")}
                    </span>
                    <div className="message-body">
                      <div className="sender-line">
                        <strong>{m.sender_display_name}</strong>
                        <span>
                          {new Date(m.timestamp).toLocaleTimeString([], {
                            hour: "2-digit",
                            minute: "2-digit",
                          })}
                        </span>
                      </div>
                      <p>{m.text}</p>
                      <div className="reason">
                        <span className="reason-icon">✧</span>
                        {m.classification?.reason ??
                          "Awaiting local classification · will retry automatically"}
                      </div>
                    </div>
                    <div className="classification-column">
                      <span
                        className={`category ${m.classification?.important ? "important" : ""}`}
                      >
                        {m.classification?.category.replaceAll("_", " ") ??
                          m.status}
                      </span>
                      <span className="score">
                        {m.classification
                          ? `${Math.round(m.classification.importance_score * 100)} / 100 importance`
                          : "Pending"}
                      </span>
                      {page === "Activity" && (
                        <small>
                          {m.classification?.model} ·{" "}
                          {number(m.classification?.latency_ms, " ms")}
                        </small>
                      )}
                    </div>
                    <ArrowUpRight size={16} className="row-arrow" />
                  </button>
                ))}
              </div>
              {!shown.length && (
                <div className="empty">
                  <Inbox size={32} />
                  <h3>
                    {query
                      ? "No matching messages"
                      : "A quieter inbox starts here"}
                  </h3>
                  <p>
                    {query
                      ? "Try another name or phrase."
                      : "Important messages will appear after the local pipeline processes them."}
                  </p>
                </div>
              )}
              <div className="panel-footer">
                <ShieldCheck size={14} /> Only you and your local model see
                these classifications.
                <span>
                  {status?.persistent
                    ? "Stored on this device"
                    : "Ephemeral session"}
                </span>
              </div>
            </section>
          )}
          {page === "Analytics" && (
            <div className="analytics-grid">
              <section className="card">
                <h2>Signal & noise</h2>
                <p>Classified messages, since the database was created</p>
                <div className="signal-bar">
                  <div
                    style={{
                      width: `${metrics.messages_processed ? (100 * (metrics.important ?? 0)) / metrics.messages_processed : 0}%`,
                    }}
                  />
                </div>
                <div className="legend">
                  <span>
                    <i />
                    Important · {metrics.important ?? 0}
                  </span>
                  <span>
                    <i />
                    Filtered · {metrics.casual ?? 0}
                  </span>
                </div>
                <Metric
                  name="Ollama invocation rate"
                  value={number(metrics.ollama_invocation_pct, "%")}
                />
                <Metric
                  name="Pre-inference filtering"
                  value={number(metrics.filtered_before_llm_pct, "%")}
                />
                <Metric
                  name="HTTP inference attempts"
                  value={number(metrics.llm_calls)}
                />
                <Metric
                  name="Pending or failed"
                  value={number(metrics.pending_or_failed)}
                />
              </section>
              <section className="card">
                <h2>Classification performance</h2>
                <p>
                  Completed classifications; benchmark for controlled
                  comparisons
                </p>
                {[
                  ["Average latency", "average_latency_ms"],
                  ["p50 latency", "p50_latency_ms"],
                  ["p95 latency", "p95_latency_ms"],
                  ["Total inference time", "total_inference_ms"],
                ].map(([name, key]) => (
                  <Metric
                    key={key}
                    name={name}
                    value={number(metrics[key], " ms")}
                  />
                ))}
                <p className="fine-print">
                  Dashboard counts persist; use the benchmark CLI for throughput
                  measurements.
                </p>
              </section>
              <section className="card quality-card">
                <div>
                  <h2>How well is your filter doing?</h2>
                  <p>
                    Label messages in the inbox to measure accuracy. Unlabeled
                    data is never treated as ground truth.
                  </p>
                </div>
                <div className="quality-values">
                  {["precision", "recall", "f1"].map((key) => (
                    <div key={key}>
                      <strong>
                        {number(
                          metrics[key] == null ? null : metrics[key]! * 100,
                          "%",
                        )}
                      </strong>
                      <span>{key.toUpperCase()}</span>
                    </div>
                  ))}
                </div>
                <small>
                  {metrics.labeled_messages ?? 0} labeled classifications ·{" "}
                  {status?.fixture
                    ? "Fixture predictions, not model evaluation"
                    : "Local labels only"}
                </small>
              </section>
            </div>
          )}
          {page === "Settings" && settings && (
            <section className="settings-panel card">
              <h2>Local intelligence</h2>
              <p>
                Changes apply to future classifications. No models are
                downloaded automatically.
              </p>
              <div className="setting">
                <div>
                  <strong>Ollama model</strong>
                  <p>Choose installed local weights. Default: qwen2.5:3b.</p>
                </div>
                <input
                  aria-label="Ollama model"
                  list="models"
                  value={settings.model}
                  onChange={(e) =>
                    setSettings({ ...settings, model: e.target.value })
                  }
                />
                <datalist id="models">
                  {models.map((m) => (
                    <option key={m} value={m} />
                  ))}
                </datalist>
              </div>
              <div className="setting">
                <div>
                  <strong>Importance threshold</strong>
                  <p>Lower values surface more messages.</p>
                </div>
                <div className="range-wrap">
                  <input
                    aria-label="Importance threshold"
                    type="range"
                    min="0.05"
                    max="1"
                    step="0.05"
                    value={settings.threshold}
                    onChange={(e) =>
                      setSettings({ ...settings, threshold: +e.target.value })
                    }
                  />
                  <output>{Math.round(settings.threshold * 100)}%</output>
                </div>
              </div>
              <Toggle
                title="Two-stage filter"
                description="Skip inference for a small set of obvious reactions without context."
                checked={settings.pipeline === "two_stage"}
                onChange={(v) =>
                  setSettings({
                    ...settings,
                    pipeline: v ? "two_stage" : "baseline_llm",
                  })
                }
              />
              <div className="setting">
                <div>
                  <strong>Conversation context</strong>
                  <p>Recent messages provided to your local model (0–12).</p>
                </div>
                <input
                  aria-label="Conversation context"
                  type="number"
                  min="0"
                  max="12"
                  value={settings.context_messages}
                  onChange={(e) =>
                    setSettings({
                      ...settings,
                      context_messages: +e.target.value,
                    })
                  }
                />
              </div>
              <div className="setting">
                <div>
                  <strong>Polling interval</strong>
                  <p>Seconds between source checks (1–3600).</p>
                </div>
                <input
                  aria-label="Polling interval"
                  type="number"
                  min="1"
                  max="3600"
                  value={settings.polling_interval}
                  onChange={(e) =>
                    setSettings({
                      ...settings,
                      polling_interval: +e.target.value,
                    })
                  }
                />
              </div>
              <h2 className="settings-subtitle">
                <Bell size={18} /> Notifications & privacy
              </h2>
              <Toggle
                title="Desktop notifications"
                description="Notify through this computer’s operating system."
                checked={settings.notifications}
                onChange={(v) => setSettings({ ...settings, notifications: v })}
              />
              <Toggle
                title="Show message previews"
                description="Include sender, message preview and reason in OS notifications."
                checked={settings.notification_previews}
                onChange={(v) =>
                  setSettings({ ...settings, notification_previews: v })
                }
              />
              <div className="save-row">
                <span role="status">{saved}</span>
                <button
                  className="primary"
                  disabled={saving}
                  onClick={() => void save()}
                >
                  <Check size={16} />
                  {saving ? "Saving…" : "Save preferences"}
                </button>
              </div>
            </section>
          )}
          <footer className="main-footer">
            <span>
              <LockKeyhole size={13} /> Private by design. Local by default.
            </span>
            <span>Made for a more intentional inbox.</span>
          </footer>
        </main>
      </div>
      {selected && (
        <div className="modal-backdrop" onClick={() => setSelected(null)}>
          <section
            className="modal card"
            role="dialog"
            aria-modal="true"
            aria-label="Message details"
            onClick={(e) => e.stopPropagation()}
          >
            <button
              className="close secondary"
              onClick={() => setSelected(null)}
            >
              Close
            </button>
            <span className="eyebrow">MESSAGE DETAILS</span>
            <h2>{selected.sender_display_name}</h2>
            <p className="full-message">{selected.text}</p>
            <p>{selected.classification?.reason ?? "Pending classification"}</p>
            <div className="detail-model">
              {selected.classification?.model} ·{" "}
              {number(selected.classification?.latency_ms, " ms")}
            </div>
            <h3>Was this important?</h3>
            <p>
              Your feedback stays local and contributes to labeled accuracy
              metrics.
            </p>
            <div className="label-actions">
              <button className="primary" onClick={() => void label(true)}>
                Important
              </button>
              <button className="secondary" onClick={() => void label(false)}>
                Not important
              </button>
            </div>
            {selected.label && (
              <p role="status">
                Saved as{" "}
                {selected.label.important ? "important" : "not important"}.
              </p>
            )}
          </section>
        </div>
      )}
    </div>
  );
}
function Stat({
  title,
  value,
  note,
  icon,
  accent = false,
}: {
  title: string;
  value: string;
  note: string;
  icon: React.ReactNode;
  accent?: boolean;
}) {
  return (
    <article className={`stat ${accent ? "accent" : ""}`}>
      <div className="stat-top">
        {title}
        {icon}
      </div>
      <strong>{value}</strong>
      <p>{note}</p>
    </article>
  );
}
function Metric({ name, value }: { name: string; value: string }) {
  return (
    <div className="metric">
      <span>{name}</span>
      <strong>{value}</strong>
    </div>
  );
}
function Toggle({
  title,
  description,
  checked,
  onChange,
}: {
  title: string;
  description: string;
  checked: boolean;
  onChange: (v: boolean) => void;
}) {
  return (
    <div className="setting">
      <div>
        <strong>{title}</strong>
        <p>{description}</p>
      </div>
      <button
        className={`toggle ${checked ? "on" : ""}`}
        role="switch"
        aria-label={title}
        aria-checked={checked}
        onClick={() => onChange(!checked)}
      >
        <span />
      </button>
    </div>
  );
}
export default App;
