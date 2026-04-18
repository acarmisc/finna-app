export type Provider = 'gcp' | 'azure' | 'aws' | 'llm' | 'ecb';
export type AlertSeverity = 'err' | 'warn' | 'ok';
export type RunStatus = 'running' | 'success' | 'failed';
export type Theme = 'light' | 'dark';
export type Density = 'compact' | 'cozy';
export type Accent = 'green' | 'indigo' | 'amber' | 'slate';
export type ToastTone = 'ok' | 'err' | 'info' | 'warn';

export interface Toast {
  id: string;
  title: string;
  body?: string;
  tone: ToastTone;
  icon?: string;
}

export interface Resource {
  id: string;
  name: string;
  type: string;
  native: string;
  mtd: number;
  tags: Record<string, string>;
}

export interface Connection {
  id: string;
  prov: Provider;
  name: string;
  scope: string;
  status: 'ok' | 'err' | 'warn';
  lastRun: string;
  rows?: string;
  auth: string;
  expires: string;
  err?: string;
  note?: string;
  projectId?: string | null;
  resources?: Resource[];
}

export interface CostRecord {
  prov: Provider;
  name: string;
  sku: string;
  mtd: number;
  delta: number;
  prev: number;
}

export interface Run {
  id: string;
  type: string;
  prov: Provider;
  status: RunStatus;
  started: string;
  dur: string;
  rows: number;
  err?: string;
}

export interface Alert {
  id: string;
  severity: AlertSeverity;
  title: string;
  body: string;
  rule: string;
  firing: string | null;
  channels: string[];
}

export interface DayData {
  day: number;
  label: string;
  gcp: number;
  azure: number;
  llm: number;
  total: number;
}

export interface Project {
  prov: Provider;
  name: string;
  skus: SKU[];
}

export interface SKU {
  sku: string;
  mtd: number;
  delta: number;
  prev: number;
}

export interface FinProject {
  id: string;
  name: string;
  slug: string;
  owner: string;
  costCenter: string;
  budgetCap: number;
  mtd: number;
  tags: Record<string, string>;
  created: string;
  note: string;
}

export interface AppData {
  PROJECTS: Project[];
  COSTS: CostRecord[];
  RUNS: Run[];
  CONNECTIONS: Connection[];
  ALERTS: Alert[];
  DAYS: DayData[];
  FIN_PROJECTS: FinProject[];
  TAG_VOCAB: Record<string, string[]>;
}

// Route type for hierarchy navigation
export type Route =
  | { screen: 'dashboard' }
  | { screen: 'explorer' }
  | { screen: 'connections' }
  | { screen: 'projects' }
  | { screen: 'project'; projectId: string }
  | { screen: 'connection'; connectionId: string }
  | { screen: 'resource'; connectionId: string; resourceId: string }
  | { screen: 'alerts' }
  | { screen: 'runs' }
  | { screen: 'budgets' }
  | { screen: 'settings' };
