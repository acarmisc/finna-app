import React from 'react';
import { TopBar } from '../common/TopBar';
import { Button } from '../common/Button';
import { ProviderTag } from '../common/ProviderTag';
import { fmt } from '../../utils/fmt';

const BUDGETS = [
  { scope: 'rg-analytics', cap: 10000, spent: 8200, provider: 'azure' },
  { scope: 'prod-platform', cap: 6000, spent: 5146, provider: 'gcp' },
  { scope: 'LLM total', cap: 2000, spent: 632, provider: 'llm' },
  { scope: 'staging-ml', cap: 1500, spent: 600, provider: 'gcp' },
  { scope: 'rg-dev', cap: 500, spent: 208, provider: 'azure' },
];

export function BudgetsScreen() {
  return (
    <div className="fn-screen" data-screen-label="Budgets">
      <TopBar title="Budgets" subtitle="Monthly caps per scope · drives alert rules"
        actions={<Button variant="primary" size="sm" icon="plus">New budget</Button>}
      />
      <div className="fn-panel fn-panel-flush">
        <table className="fn-table">
          <thead><tr>
            <th>Scope</th><th>Provider</th>
            <th style={{ width: '40%' }}>Utilization</th>
            <th className="num">Spent</th>
            <th className="num">Cap</th>
            <th className="num">Remaining</th>
          </tr></thead>
          <tbody>
            {BUDGETS.map((b, i) => {
              const pct = b.spent / b.cap;
              const over = pct > 0.8;
              return (
                <tr key={i}>
                  <td className="mono">{b.scope}</td>
                  <td><ProviderTag p={b.provider} /></td>
                  <td>
                    <div className="fn-budget-bar">
                      <div className="fn-budget-fill" style={{
                        width: (Math.min(pct, 1) * 100) + '%',
                        background: over ? 'var(--danger)' : 'var(--primary)',
                      }} />
                      <span className="fn-budget-pct mono">{(pct * 100).toFixed(0)}%</span>
                    </div>
                  </td>
                  <td className="num mono fn-strong">{fmt.money(b.spent)}</td>
                  <td className="num mono fn-muted">{fmt.money(b.cap)}</td>
                  <td className={`num mono fn-${over ? 'up' : 'down'}`}>{fmt.money(b.cap - b.spent)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
