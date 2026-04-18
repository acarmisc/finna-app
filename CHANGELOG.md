# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2026-04-18

### Added
- **Plugin-based Extractor System**: New architecture for data extraction.
  - `backend/extractors/base.py`: Abstract Base Class for plugins with automatic registry.
  - `backend/extractors/plugins.py`: Dynamic discovery and registration of built-in and 3rd party extractors.
  - Dynamic frontend forms: `NewConnectionModal` now renders fields based on plugin metadata from the API.
- **Sample Data Seeding**: 
  - `resources/fixtures/sample_data.json`: Realistic mock data for cloud costs, LLM usage, and runs.
  - `scripts/seed.py`: Idempotent script to populate a fresh database.
  - `make seed` target in Makefile.
- **Frontend Build System**: Bootstrapped React shell into a functional Vite application.
- **Enhanced Documentation**: Added guides for architecture, dev setup, and plugin development.

### Changed
- **Major Project Reorganization**: Restructured the repository for clarity between backend, frontend, CLI, and deployment.
  - `backend/`: Core logic, API (now `backend/app/`), extractors, and migrations.
  - `frontend/`: Isolated React/Vite project.
  - `cli/`: Command-line tools and wizards.
  - `deploy/`: Containerization (Docker, Compose) and K8s manifests.
  - `resources/`: Shared assets, SQL scripts, fixtures, and dashboards.
- **Unified Provider Enums**: Synchronized cloud provider lists across backend and frontend (Azure, GCP, AWS, LLM, ECB).
- **Stabilized Infrastructure**: 
  - Resilient database migrations: Detects missing PostgreSQL extensions (`pg_partman`, `pg_cron`) and skips partitioning setup gracefully on standard images.
  - Fixed `alembic` configuration and Python driver compatibility.

### Fixed
- Resolved multiple TypeScript and build errors in the frontend.
- Fixed subprocess record parsing in the API runner.
- Resolved various race conditions and import errors caused by the directory structure refactor.

## [0.1.0] - 2026-04-14

### Added
- **FastAPI Orchestrator**: New API service for cloud credential management.
- **CLI Integration**: Auth flags for pushing config to the API.
- **Docker Integration**: API and Extractor container definitions.

### Fixed
- Subprocess record parsing logic.
- Most recent config selection strategy.

---

## [Previous Sessions]
See git log for earlier changes.
