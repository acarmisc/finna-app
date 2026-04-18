import React, { useState } from 'react';
import { TopBar } from '../common/TopBar';
import { Button } from '../common/Button';
import { Icon } from '../common/Icon';
import { Skeleton } from '../common/Skeleton';
import { ErrorMessage } from '../common/ErrorMessage';
import { useConfigs } from '../../api/queries';
import { useTheme } from '../../hooks/useTheme';

export function SettingsScreen() {
  const { theme, density, accent, setTheme, setDensity, setAccent } = useTheme();
  const { data: configs, loading, error, refetch } = useConfigs();

  return (
    <div className="fn-screen" data-screen-label="Settings">
      <TopBar title="Settings" subtitle="Workspace · integrations · data retention" />
      <div className="fn-settings-grid">
        <TweaksPanel
          theme={theme}
          density={density}
          accent={accent}
          setTheme={setTheme}
          setDensity={setDensity}
          setAccent={setAccent}
        />
        <SettingsCard icon="building-2" title="Workspace"
          fields={[['Name', 'Acme Platform'], ['Slug', 'acme'], ['Default currency', 'USD (ECB normalized)']]} />
        <SettingsCard icon="database" title="PostgreSQL"
          fields={[
            ['PG_DSN', 'postgresql://finops:••••@db.acme.co:5432/finops'],
            ['Schema version', 'v1.4'],
            ['Partition', 'monthly'],
            ['Seed data', '90 days'],
          ]} />
        <SettingsCard icon="calendar" title="Schedule"
          fields={[
            ['Nightly extraction', '02:00 UTC'],
            ['ECB rates', '16:05 UTC'],
            ['LLM OTel polling', 'every 5m'],
          ]} />
        <SettingsCard icon="cloud" title="Cloud Configurations"
          loading={loading}
          errorMsg={error}
          onRetry={refetch}
          fields={configs ? configs.map(c => [c.name, `${c.provider} · ${c.credential_type}`] as [string, string]) : []} />
        <SettingsCard icon="shield" title="Authentication"
          fields={[
            ['Azure token cache', 'OS keyring'],
            ['GCP ADC', 'gcloud auth'],
            ['Retention', '12 months'],
          ]} />
      </div>
    </div>
  );
}

function TweaksPanel({ theme, density, accent, setTheme, setDensity, setAccent }: {
  theme: string;
  density: string;
  accent: string;
  setTheme: (t: string) => void;
  setDensity: (d: string) => void;
  setAccent: (a: string) => void;
}) {
  return (
    <div className="fn-panel">
      <div className="fn-panel-head">
        <h3>Appearance</h3>
        <div className="fn-sub">Customize interface density, theme, and accent color</div>
      </div>
      <div className="fn-tweaks-grid">
        <div className="fn-tweak-section">
          <div className="fn-tweak-label">Density</div>
          <div className="fn-seg">
            <button
              className={`fn-seg-btn ${density === 'compact' ? 'is-active' : ''}`}
              onClick={() => setDensity('compact')}
            >
              Compact
            </button>
            <button
              className={`fn-seg-btn ${density === 'comfortable' ? 'is-active' : ''}`}
              onClick={() => setDensity('comfortable')}
            >
              Comfortable
            </button>
          </div>
        </div>

        <div className="fn-tweak-section">
          <div className="fn-tweak-label">Theme</div>
          <div className="fn-seg">
            <button
              className={`fn-seg-btn ${theme === 'light' ? 'is-active' : ''}`}
              onClick={() => setTheme('light')}
            >
              Light
            </button>
            <button
              className={`fn-seg-btn ${theme === 'dark' ? 'is-active' : ''}`}
              onClick={() => setTheme('dark')}
            >
              Dark
            </button>
          </div>
        </div>

        <div className="fn-tweak-section">
          <div className="fn-tweak-label">Accent</div>
          <div className="fn-seg">
            {['green', 'indigo', 'amber', 'slate'].map(ac => (
              <button
                key={ac}
                className={`fn-seg-btn ${accent === ac ? 'is-active' : ''}`}
                onClick={() => setAccent(ac)}
              >
                <span className="fn-accent-preview"
                  style={{
                    width: 12,
                    height: 12,
                    borderRadius: 2,
                    background:
                      ac === 'green' ? 'oklch(0.58 0.14 150)' :
                      ac === 'indigo' ? 'oklch(0.52 0.18 275)' :
                      ac === 'amber' ? 'oklch(0.70 0.17 75)' :
                      'oklch(0.40 0.020 265)',
                    display: 'inline-block'
                  }}
                />
                <span className="fn-accent-label">{ac}</span>
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

function SettingsCard({ icon, title, fields, loading, errorMsg, onRetry }: {
  icon: string;
  title: string;
  fields: [string, string][];
  loading?: boolean;
  errorMsg?: string | null;
  onRetry?: () => void;
}) {
  return (
    <div className="fn-panel">
      <div className="fn-panel-head">
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <Icon name={icon} size={16} style={{ color: 'var(--fg-muted)' }} />
          <h3>{title}</h3>
        </div>
        <Button variant="ghost" size="sm" icon="pencil">Edit</Button>
      </div>
      {loading ? (
        <div style={{ padding: 16 }}><Skeleton height={16} /><Skeleton height={16} /></div>
      ) : errorMsg ? (
        <ErrorMessage message={`Failed to load: ${errorMsg}`} onRetry={onRetry} />
      ) : (
        <div className="fn-kv-list">
          {fields.map(([k, v], i) => (
            <div key={i} className="fn-kv">
              <span className="fn-k">{k}</span>
              <span className="fn-v mono">{v}</span>
            </div>
          ))}
          {fields.length === 0 && <div className="fn-empty" style={{ padding: 16, color: 'var(--fg-subtle)' }}>No items.</div>}
        </div>
      )}
    </div>
  );
}
