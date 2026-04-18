import React, { useState, useMemo } from 'react';
import { TopBar } from '../common/TopBar';
import { StatCard } from '../common/StatCard';
import { Button } from '../common/Button';
import { Badge } from '../common/Badge';
import { ProviderTag, ProviderDot } from '../common/ProviderTag';
import { Icon } from '../common/Icon';
import { Skeleton } from '../common/Skeleton';
import { ErrorMessage } from '../common/ErrorMessage';
import { useExtractorRuns } from '../../api/queries';
import { fmt } from '../../utils/fmt';
import { FINNA_DATA } from '../../data';
import type { Toast, DayData, CostRecord, Run } from '../../types';

interface DashboardScreenProps {
  pushToast: (toast: Omit<Toast, 'id'>) => void;
}

export function DashboardScreen({ pushToast }: DashboardScreenProps) {
  const { data: runsData, loading: runsLoading, error: runsError, refetch: refetchRuns } = useExtractorRuns();
  const { COSTS, DAYS, ALERTS, PROJECTS } = FINNA_DATA;
  const RUNS: Run[] = runsData
    ? runsData.map(r => ({
        id: r.id,
        type: r.extractor_type,
        prov: (r.provider || 'ecb') as any,
        status: r.status === 'running' ? 'running' : r.status === 'success' ? 'success' : 'failed',
        started: r.started_at,
        dur: r.finished_at && r.started_at
          ? (() => { const d = new Date(r.finished_at).getTime() - new Date(r.started_at).getTime(); return d < 60000 ? `${Math.round(d/1000)}s` : `${Math.floor(d/60000)}m ${Math.round((d%60000)/1000)}s`; })()
          : '—',
        rows: r.records_extracted,
        err: r.error_message || undefined,
      }))
    : FINNA_DATA.RUNS;

  const [range, setRange] = useState<'mtd' | 'ytd' | '90d'>('mtd');
  const [hover, setHover] = useState<DayData | null>(null);
  const [provFilter, setProvFilter] = useState('all');
  const [projFilter, setProjFilter] = useState('all');
  const [dateOpen, setDateOpen] = useState(false);
  const [provOpen, setProvOpen] = useState(false);
  const [projOpen, setProjOpen] = useState(false);

  const firing = ALERTS.filter(a => a.severity !== 'ok').length;
  const projectOptions = Array.from(new Set(PROJECTS.map(p => p.name)));
  const provOptions: [string, string][] = [['all', 'All providers'], ['gcp', 'GCP'], ['azure', 'Azure'], ['llm', 'LLM']];

  const FilterChip = ({
    icon, label, value, open, onToggle, children,
  }: {
    icon: string; label: string; value: string;
    open: boolean; onToggle: () => void; children: React.ReactNode;
  }) => (
    <div style={{ position: 'relative' }} role="combobox" aria-expanded={open} aria-haspopup="listbox">
      <button
        className="fn-btn fn-btn-outline fn-btn-sm"
        onClick={onToggle}
        aria-label={`${label}: ${value}`}
        aria-expanded={open}
      >
        <Icon name={icon} size={13} aria-hidden />
        <span style={{ color: 'var(--fg-subtle)' }}>{label}:</span>
        <span style={{ fontWeight: 500 }}>{value}</span>
        <Icon name="chevron-down" size={12} aria-hidden />
      </button>
      {open && (
        <>
          <div style={{ position: 'fixed', inset: 0, zIndex: 20 }} onClick={onToggle} aria-hidden="true" />
          <div
            role="listbox"
            style={{
              position: 'absolute', top: 'calc(100% + 4px)', right: 0, zIndex: 21,
              background: 'var(--bg-surface)', border: '1px solid var(--border)',
              borderRadius: 'var(--radius-md)', boxShadow: 'var(--shadow-md)',
              padding: 4, minWidth: 200, maxHeight: 280, overflowY: 'auto',
            }}
          >
            {children}
          </div>
        </>
      )}
    </div>
  );

  const MenuItem = ({ active, onClick, children }: { active: boolean; onClick: () => void; children: React.ReactNode }) => (
    <button
      onClick={onClick}
      role="option"
      aria-selected={active}
      style={{
        display: 'flex', alignItems: 'center', gap: 8, width: '100%',
        padding: '8px 10px', border: 0,
        background: active ? 'var(--bg-accent)' : 'transparent',
        borderRadius: 'var(--radius-sm)', cursor: 'pointer',
        fontSize: 13, color: 'var(--fg)', textAlign: 'left',
      }}
    >
      <span style={{ width: 14, display: 'inline-grid', placeItems: 'center' }} aria-hidden="true">
        {active && <Icon name="check" size={12} style={{ color: 'var(--brand-green, var(--primary))' }} />}
      </span>
      {children}
    </button>
  );

  const runsEl = runsLoading
    ? <div className="fn-runs"><Skeleton height={40} /><Skeleton height={40} /></div>
    : runsError
    ? <ErrorMessage message={`Failed to load runs: ${runsError}`} onRetry={refetchRuns} />
    : <div className="fn-runs">{RUNS.slice(0, 5).map(r => <RunRow key={r.id} r={r} />)}</div>;

  return (
    <div className="fn-screen" data-screen-label="Dashboard">
      <TopBar
        title="Overview"
        subtitle={`All costs normalized to USD via ECB · last refresh 4 min ago${provFilter !== 'all' || projFilter !== 'all' ? ' · filtered' : ''}`}
        actions={<>
          <FilterChip icon="calendar" label="Date" value="Nov 1 – 14, 2025" open={dateOpen} onToggle={() => setDateOpen(o => !o)}>
            {[['Nov 1 – 14, 2025', 'MTD'], ['Oct 2025', 'Last month'], ['Last 7 days', '7d'], ['Last 90 days', '90d'], ['YTD 2025', 'YTD']].map(([l, sub]) => (
              <MenuItem key={l} active={l === 'Nov 1 – 14, 2025'} onClick={() => setDateOpen(false)}>
                <span style={{ flex: 1 }}>{l}</span>
                <span style={{ color: 'var(--fg-subtle)', fontSize: 11 }}>{sub}</span>
              </MenuItem>
            ))}
          </FilterChip>
          <FilterChip icon="cloud" label="Provider"
            value={provOptions.find(([k]) => k === provFilter)![1]}
            open={provOpen} onToggle={() => setProvOpen(o => !o)}>
            {provOptions.map(([k, l]) => (
              <MenuItem key={k} active={provFilter === k} onClick={() => { setProvFilter(k); setProvOpen(false); }}>
                {k !== 'all' && <ProviderDot p={k} />} {l}
              </MenuItem>
            ))}
          </FilterChip>
          <FilterChip icon="folder" label="Project"
            value={projFilter === 'all' ? 'All projects' : projFilter}
            open={projOpen} onToggle={() => setProjOpen(o => !o)}>
            <MenuItem active={projFilter === 'all'} onClick={() => { setProjFilter('all'); setProjOpen(false); }}>All projects</MenuItem>
            {projectOptions.map(n => (
              <MenuItem key={n} active={projFilter === n} onClick={() => { setProjFilter(n); setProjOpen(false); }}>
                <span className="mono" style={{ fontSize: 12 }}>{n}</span>
              </MenuItem>
            ))}
          </FilterChip>
          <Button variant="outline" size="sm" icon="refresh-cw"
            onClick={() => { refetchRuns(); pushToast({ tone: 'ok', title: 'Extractors queued', body: '4 extractors scheduled · ~90s' }); }}>
            Run now
          </Button>
          <Button variant="primary" size="sm" icon="download">Export</Button>
        </>}
      />

      <div className="fn-stats-row">
        <StatCard label="MTD spend · USD" value={fmt.money(8412.05)} delta="+42.1% vs last month" tone="up"
          meta="14 days elapsed" sparkline={DAYS.slice(0, 14).map(d => d.total)} />
        <StatCard label="Forecast · month end" value={fmt.money(17240, { compact: true })} delta="+18.0%"
          tone="up" meta="exceeds $15K budget" sparkline={DAYS.map(d => d.total)} />
        <StatCard label="Anomalies (7d)" value="3" delta={`${firing} firing now`} tone="up" meta="2 warn · 1 critical" />
        <StatCard label="Connections" value="7" delta="1 failing" tone="flat" meta="3 Azure · 2 GCP · 2 LLM" />
      </div>

      <div className="fn-panel">
        <div className="fn-panel-head">
          <div>
            <h3>Cost by provider</h3>
            <div className="fn-sub">Stacked daily · normalized USD · 30 day window</div>
          </div>
          <div className="fn-seg">
            {(['mtd', 'ytd', '90d'] as const).map(k => (
              <button key={k} className={`fn-seg-btn ${range === k ? 'is-active' : ''}`} onClick={() => setRange(k)}>
                {{ mtd: 'MTD', ytd: 'YTD', '90d': 'Last 90d' }[k]}
              </button>
            ))}
          </div>
        </div>
        <DashboardChart data={DAYS} onHover={setHover} hover={hover} />
        <div className="fn-chart-legend">
          <span><span className="fn-sq" style={{ background: '#4285F4' }} />GCP · {fmt.money(DAYS.reduce((a, d) => a + d.gcp, 0))}</span>
          <span><span className="fn-sq" style={{ background: '#0078D4' }} />Azure · {fmt.money(DAYS.reduce((a, d) => a + d.azure, 0))}</span>
          <span><span className="fn-sq" style={{ background: 'oklch(0.55 0.18 300)' }} />LLM · {fmt.money(DAYS.reduce((a, d) => a + d.llm, 0))}</span>
          {hover && <span className="fn-chart-hover mono">{hover.label}: {fmt.money(hover.total)}</span>}
        </div>
      </div>

      <div className="fn-two-col">
        <div className="fn-panel">
          <div className="fn-panel-head">
            <div>
              <h3>Top spenders · MTD</h3>
              <div className="fn-sub">Ranked by normalized USD</div>
            </div>
            <a href="#" onClick={e => e.preventDefault()}>View all →</a>
          </div>
          <TopSpendersTable rows={[...COSTS].sort((a, b) => b.mtd - a.mtd).slice(0, 6)} />
        </div>
        <div className="fn-panel">
          <div className="fn-panel-head">
            <div>
              <h3>Recent extractor runs</h3>
              <div className="fn-sub">From extractor_runs · last 5</div>
            </div>
            <a href="#" onClick={e => e.preventDefault()}>Run log →</a>
          </div>
          {runsEl}
        </div>
      </div>

      <div className="fn-panel">
        <div className="fn-panel-head">
          <div><h3>Active alerts</h3><div className="fn-sub">{firing} firing · surfaced from alert_queries.sql</div></div>
          <a href="#" onClick={e => e.preventDefault()}>All alerts →</a>
        </div>
        <div className="fn-alert-list">
          {ALERTS.filter(a => a.severity !== 'ok').slice(0, 3).map(a => (
            <div key={a.id} className={`fn-alert-strip fn-alert-${a.severity}`}>
              <Badge tone={a.severity}>{a.severity === 'err' ? 'critical' : 'warn'}</Badge>
              <div>
                <div className="fn-alert-title">{a.title}</div>
                <div className="fn-alert-body">{a.body}</div>
              </div>
              <div className="fn-alert-when mono">fired {a.firing}</div>
              <Button size="sm" variant="ghost" icon="arrow-right">Open</Button>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function DashboardChart({ data, onHover, hover }: { data: DayData[]; onHover: (d: DayData | null) => void; hover: DayData | null }) {
  const w = 1100, h = 240, pad = { t: 12, r: 16, b: 24, l: 48 };
  const max = Math.max(...data.map(d => d.total)) * 1.1;
  const innerW = w - pad.l - pad.r;
  const innerH = h - pad.t - pad.b;
  const barW = innerW / data.length - 4;
  const yTicks = [0, 0.25, 0.5, 0.75, 1].map(t => ({ v: max * t, y: pad.t + innerH - innerH * t }));

  return (
    <div className="fn-chart-wrap">
      <svg viewBox={`0 0 ${w} ${h}`} className="fn-chart-svg" preserveAspectRatio="none">
        {yTicks.map((t, i) => (
          <g key={i}>
            <line x1={pad.l} x2={w - pad.r} y1={t.y} y2={t.y} stroke="var(--border-subtle)" strokeDasharray={i === 0 ? '' : '2 4'} />
            <text x={pad.l - 8} y={t.y + 3} textAnchor="end" fontSize="10" fill="var(--fg-subtle)" fontFamily="var(--font-mono)">
              {i === 0 ? '0' : '$' + Math.round(t.v).toLocaleString()}
            </text>
          </g>
        ))}
        {data.map((d, i) => {
          const x = pad.l + i * (innerW / data.length) + 2;
          const gcpH = (d.gcp / max) * innerH;
          const azureH = (d.azure / max) * innerH;
          const llmH = (d.llm / max) * innerH;
          const yBase = pad.t + innerH;
          return (
            <g key={d.day}
              onMouseEnter={() => onHover(d)}
              onMouseLeave={() => onHover(null)}
              className={`fn-bar-g ${hover?.day === d.day ? 'is-hover' : ''}`}>
              <rect x={x} y={yBase - gcpH} width={barW} height={gcpH} fill="#4285F4" />
              <rect x={x} y={yBase - gcpH - azureH} width={barW} height={azureH} fill="#0078D4" />
              <rect x={x} y={yBase - gcpH - azureH - llmH} width={barW} height={llmH} fill="oklch(0.55 0.18 300)" />
              <rect x={x - 2} y={pad.t} width={barW + 4} height={innerH} fill="transparent" />
            </g>
          );
        })}
        {data.filter((_, i) => i % 5 === 0).map((d, i) => {
          const idx = i * 5;
          const x = pad.l + idx * (innerW / data.length) + 2 + barW / 2;
          return (
            <text key={d.day} x={x} y={h - 6} textAnchor="middle" fontSize="10" fill="var(--fg-subtle)" fontFamily="var(--font-mono)">
              {d.label}
            </text>
          );
        })}
      </svg>
    </div>
  );
}

function TopSpendersTable({ rows }: { rows: CostRecord[] }) {
  const max = Math.max(...rows.map(r => r.mtd));
  return (
    <table className="fn-table is-compact">
      <thead><tr>
        <th>Provider</th><th>Project · SKU</th><th></th><th className="num">MTD</th><th className="num">Δ</th>
      </tr></thead>
      <tbody>{rows.map((r, i) => (
        <tr key={i}>
          <td style={{ width: 80 }}><ProviderTag p={r.prov} /></td>
          <td>
            <div className="mono">{r.name}</div>
            <div className="fn-cell-sub">{r.sku}</div>
          </td>
          <td style={{ width: 120 }}>
            <div className="fn-bar-inline">
              <div style={{ width: (r.mtd / max * 100) + '%', background: 'var(--fg-muted)' }} />
            </div>
          </td>
          <td className="num mono">{fmt.money(r.mtd)}</td>
          <td className={`num mono fn-${r.delta > 0 ? 'up' : r.delta < 0 ? 'down' : 'flat'}`}>{fmt.pct(r.delta)}</td>
        </tr>
      ))}</tbody>
    </table>
  );
}

export function RunRow({ r, onClick }: { r: Run; onClick?: () => void }) {
  const tone = r.status === 'success' ? 'ok' : r.status === 'running' ? 'info' : 'err';
  return (
    <div className={`fn-run ${onClick ? 'is-clickable' : ''}`} onClick={onClick}>
      <Badge tone={tone} dot>{r.status}</Badge>
      <span className="mono fn-run-type">{r.type}</span>
      <ProviderDot p={r.prov} />
      <span className="fn-run-meta mono">{r.started} · {r.dur} · {r.rows.toLocaleString()} rows</span>
      {r.err && <span className="fn-run-err mono">{r.err}</span>}
    </div>
  );
}
