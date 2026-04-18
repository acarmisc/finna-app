export interface CloudConfig {
  id: string;
  provider: string;
  name: string;
  credential_type: string;
  config: Record<string, any>;
  created_at: string;
  updated_at: string;
}

export interface ExtractorRun {
  id: string;
  config_id: string;
  provider: string;
  extractor_type: string;
  status: string;
  started_at: string;
  finished_at: string | null;
  records_extracted: number;
  error_message: string | null;
}

export interface ExtractorHealth {
  name: string;
  status: string;
  last_run: string;
  records_count: number;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface HealthResponse {
  status: string;
  api: string;
  database?: string;
}
