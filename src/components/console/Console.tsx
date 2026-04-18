import React, { useState, useEffect, useCallback } from 'react';
import { Sidebar } from './Sidebar';
import { DashboardScreen } from '../screens/DashboardScreen';
import { ExplorerScreen } from '../screens/ExplorerScreen';
import { ConnectionsScreen } from '../screens/ConnectionsScreen';
import { AlertsScreen } from '../screens/AlertsScreen';
import { RunsScreen } from '../screens/RunsScreen';
import { BudgetsScreen } from '../screens/BudgetsScreen';
import { SettingsScreen } from '../screens/SettingsScreen';
import { CommandPalette } from './CommandPalette';
import { NewConnectionModal } from './modals/NewConnectionModal';
import { ConnectionDrawer } from './drawers/ConnectionDrawer';
import { CostDrawer } from './drawers/CostDrawer';
import { RunDrawer } from './drawers/RunDrawer';
import { Toaster } from './Toaster';
import { useTheme } from '../hooks/useTheme';
import { useLocalStorage } from '../hooks/useLocalStorage';
import type { Toast, Connection, CostRecord, Run } from '../types';
import './Console.css';

const SCREENS = [
  { id: 'dashboard', label: 'Dashboard', icon: 'gauge' },
  { id: 'explorer', label: 'Cost explorer', icon: 'chart-line' },
  { id: 'connections', label: 'Connections', icon: 'plug' },
  { id: 'alerts', label: 'Alerts', icon: 'bell' },
  { id: 'runs', label: 'Run log', icon: 'database' },
  { id: 'budgets', label: 'Budgets', icon: 'wallet' },
  { id: 'settings', label: 'Settings', icon: 'settings' },
];

type ScreenId = typeof SCREENS[number]['id'];

export function Console() {
  const [screen, setScreen] = useLocalStorage<ScreenId>('finna-screen', 'dashboard');
  const [collapsed, setCollapsed] = useLocalStorage('finna-collapsed', false);
  const [cmdOpen, setCmdOpen] = useState(false);
  const [newConn, setNewConn] = useState(false);
  const [drawerConn, setDrawerConn] = useState<Connection | null>(null);
  const [drawerCost, setDrawerCost] = useState<CostRecord | null>(null);
  const [drawerRun, setDrawerRun] = useState<Run | null>(null);
  const [toasts, setToasts] = useState<Toast[]>([]);
  const { theme, accent, density, setTheme, setAccent, setDensity } = useTheme();

  // Command palette with Cmd+K
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        setCmdOpen(o => !o);
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, []);

  const pushToast = useCallback((toast: Omit<Toast, 'id'>) => {
    const id = Math.random().toString(36).slice(2, 8);
    setToasts(ts => [...ts, { id, ...toast }]);
    setTimeout(() => setToasts(ts => ts.filter(t => t.id !== id)), 4500);
  }, []);

  const dismissToast = useCallback((id: string) => {
    setToasts(ts => ts.filter(t => t.id !== id));
  }, []);

  let screenEl: React.ReactNode;
  switch (screen) {
    case 'explorer':
      screenEl = <ExplorerScreen pushToast={pushToast} onOpenCost={setDrawerCost} />;
      break;
    case 'connections':
      screenEl = <ConnectionsScreen pushToast={pushToast} onNew={() => setNewConn(true)} onOpen={setDrawerConn} />;
      break;
    case 'alerts':
      screenEl = <AlertsScreen pushToast={pushToast} />;
      break;
    case 'runs':
      screenEl = <RunsScreen onOpenRun={setDrawerRun} />;
      break;
    case 'budgets':
      screenEl = <BudgetsScreen />;
      break;
    case 'settings':
      screenEl = <SettingsScreen />;
      break;
    default:
      screenEl = <DashboardScreen pushToast={pushToast} />;
  }

  return (
    <div
      className={`fn-app ${collapsed ? 'is-collapsed' : ''}`}
      data-theme={theme}
      data-density={density === 'compact' ? 'compact' : 'cozy'}
      style={{
        '--accent-brand': `var(--accent-${accent}-brand)`,
        '--accent-weak': `var(--accent-${accent}-weak)`,
        '--accent-ink': `var(--accent-${accent}-ink)`,
      } as React.CSSProperties}
    >
      <Sidebar
        current={screen}
        onNav={setScreen}
        onOpenCmd={() => setCmdOpen(true)}
        collapsed={collapsed}
        onToggle={() => setCollapsed(c => !c)}
      />
      <main className="fn-main">{screenEl}</main>

      <NewConnectionModal
        open={newConn}
        onClose={() => setNewConn(false)}
        onCreate={(c) => {
          pushToast({ tone: 'ok', title: `Created ${c.name}`, body: `${c.prov.toUpperCase()} · dry-run scheduled` });
        }}
      />
      <ConnectionDrawer c={drawerConn} onClose={() => setDrawerConn(null)} pushToast={pushToast} />
      <CostDrawer row={drawerCost} onClose={() => setDrawerCost(null)} />
      <RunDrawer run={drawerRun} onClose={() => setDrawerRun(null)} />
      <CommandPalette open={cmdOpen} onClose={() => setCmdOpen(false)} onNav={setScreen} screens={SCREENS} />
      <Toaster toasts={toasts} dismiss={dismissToast} />
    </div>
  );
}
