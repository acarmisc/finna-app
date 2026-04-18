import React, { useState } from 'react';
import { TopBar } from '../common/TopBar';
import { Button } from '../common/Button';
import { Badge } from '../common/Badge';
import { Icon } from '../common/Icon';
import { Skeleton } from '../common/Skeleton';
import { ErrorMessage } from '../common/ErrorMessage';
import { useExtractorHealth } from '../../api/queries';
import type { Toast, Alert } from '../../types';

interface AlertsScreenProps {
  pushToast: (toast: Omit<Toast, 'id'>) => void;
}

export function AlertsScreen({ pushToast }: AlertsScreenProps) {
  const { data: healthData, loading, error, refetch } = useExtractorHealth();
  const [tab, setTab] = useState<'firing' | 'resolved' | 'all'>('firing');

  const ALERTS: Alert[] = healthData
    ? healthData.map((h, i) => ({
        id: `a_health_${i}`,
        severity: h.status === 'ok' ? 'ok' as const : h.status === 'warn' ? 'warn' as const : 'err' as const,
        title: h.name,
        body: `Status: ${h.status} · ${h.records_count} records · last run ${h.last_run}`,
        rule: `extractor_health.last_success < 6h`,
        firing: h.status !== 'ok' ? 'recently' : null,
        channels: ['#finops · Slack'],
      }))
    : [];

  const list = tab === 'firing'
    ? ALERTS.filter(a => a.severity !== 'ok')
    : tab === 'resolved'
    ? ALERTS.filter(a => a.severity === 'ok')
    : ALERTS;

  if (loading) {
    return (
      <div className="fn-screen" data-screen-label="Alerts">
        <TopBar title="Alerts" subtitle="Loading..." />
        <div style={{ padding: 24 }}><Skeleton height={80} /><Skeleton height={80} /></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="fn-screen" data-screen-label="Alerts">
        <TopBar title="Alerts" subtitle="Error" />
        <ErrorMessage message={`Failed to load alerts: ${error}`} onRetry={refetch} />
      </div>
    );
  }

  return (
    <div className="fn-screen" data-screen-label="Alerts">
      <TopBar title="Alerts"
        subtitle={`${ALERTS.filter(a => a.severity !== 'ok').length} firing · ${ALERTS.length} rules`}
        actions={<>
          <Button variant="outline" size="sm" icon="bell-off">Snooze all</Button>
          <Button variant="primary" size="sm" icon="plus">New rule</Button>
        </>}
      />
      <div className="fn-tabs-bar">
        {([
          ['firing', 'Firing', ALERTS.filter(a => a.severity !== 'ok').length],
          ['resolved', 'Resolved', ALERTS.filter(a => a.severity === 'ok').length],
          ['all', 'All', ALERTS.length],
        ] as [string, string, number][]).map(([k, l, n]) => (
          <button key={k} className={`fn-tab ${tab === k ? 'is-active' : ''}`} onClick={() => setTab(k as typeof tab)}>
            {l}<span className="fn-tab-count">{n}</span>
          </button>
        ))}
      </div>
      <div className="fn-alerts">
        {list.map(a => (
          <AlertCard key={a.id} a={a}
            onSnooze={() => pushToast({ tone: 'info', title: `Snoozed ${a.title}`, body: 'Will recheck in 1h' })} />
        ))}
        {list.length === 0 && <div className="fn-empty" style={{ padding: 40, textAlign: 'center', color: 'var(--fg-subtle)' }}>No alerts to display.</div>}
      </div>
    </div>
  );
}

function AlertCard({ a, onSnooze }: { a: Alert; onSnooze: () => void }) {
  const label = { ok: 'Resolved', warn: 'Firing · warn', err: 'Firing · critical' }[a.severity];
  return (
    <div className={`fn-panel fn-alert fn-alert-${a.severity}`}>
      <div className="fn-alert-head">
        <Badge tone={a.severity} dot>{label}</Badge>
        <h3>{a.title}</h3>
        {a.firing && <span className="fn-sub">triggered {a.firing}</span>}
      </div>
      <div className="fn-alert-body">{a.body}</div>
      <pre className="fn-alert-rule mono">{a.rule}</pre>
      <div className="fn-alert-chans">
        <Icon name="send" size={12} />
        <span>Notifies</span>
        {a.channels.map((ch, i) => <span key={i} className="fn-chip fn-chip-sm mono">{ch}</span>)}
      </div>
      <div className="fn-alert-foot">
        <Button variant="outline" size="sm" icon="chart-line">View in Explorer</Button>
        <Button variant="ghost" size="sm" icon="bell-off" onClick={onSnooze}>Snooze 1h</Button>
        <Button variant="ghost" size="sm" icon="pencil">Edit rule</Button>
      </div>
    </div>
  );
}
