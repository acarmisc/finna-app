# System Architecture

Finna is a multi-cloud FinOps monitoring and orchestration platform. It is designed to ingest, normalize, and visualize cost and infrastructure data from various sources.

## Core Components

### 1. API (Backend)
-   **Framework**: FastAPI (Python 3.11+)
-   **Database**: PostgreSQL 16
-   **Authentication**: JWT-based auth with support for cloud provider device flows.
-   **Responsibilities**:
    -   Orchestrating extractor runs.
    -   Managing cloud configurations and credentials.
    -   Serving normalized data to the frontend.
    -   Exposing Prometheus metrics and OpenTelemetry traces.

### 2. Extractors (Worker)
-   **Architecture**: Plugin-based.
-   **Responsibilities**: 
    -   Interfacing with cloud provider APIs (GCP, Azure, AWS).
    -   Normalizing disparate cost data formats into a unified schema.
    -   Writing data to PostgreSQL.
-   **Execution**: Can be run as standalone Docker containers or triggered by the API runner.

### 3. Frontend (UI)
-   **Framework**: React 18, TypeScript, Vite.
-   **Styling**: Custom CSS with design tokens (Theme/Density/Accent).
-   **State Management**: Hooks-based with API client caching.
-   **Responsibilities**:
    -   Visualizing cost trends and infrastructure metrics.
    -   Managing connections and projects.
    -   Monitoring extraction health and alerts.

## Data Flow

1.  **Ingestion**: Extractors fetch raw billing data from cloud providers.
2.  **Normalization**: Data is mapped to the `NormalizedCostRecord` schema.
3.  **Storage**: Records are written to the `cost_records` table (partitioned by month).
4.  **Aggregation**: Materialized views (like `daily_costs`) pre-calculate dashboard metrics.
5.  **Visualization**: The React UI queries the API to render charts and tables.

## Deployment Stack

-   **Docker Compose**: Standard local development and small-scale deployment.
-   **Kubernetes**: Production deployment (manifests in `/k8s`).
-   **Monitoring**: Prometheus for metrics, Jaeger/Tempo for traces, Superset for advanced BI.
