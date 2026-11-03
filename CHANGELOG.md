# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Admin endpoints for creating and updating tenants (`POST`/`PUT /api/admin/tenants`).
- Endpoints for creating and listing users (`POST`/`GET /api/auth/users`).
- Unit tests for authentication and tenant/user management.

### Changed
- Enforce unique tenant names and domains via unique MongoDB indexes.

### Security
- Fixed unauthenticated dataset write endpoints (`POST`/`PUT /api/datasets`), which previously allowed
  requests without admin credentials to create or modify datasets.
- Fixed a server-side request forgery (SSRF) vulnerability in the CMDI connector.
- Hardened Host-header based tenant/admin domain resolution.

## [0.1.3] - 2026-10-29

### Fixed
- Fixed a bug caused by incorrect enum comparison.

## [0.1.2] - 2026-10-29

### Changed
- Migrated the database driver from Motor to PyMongo.

### Fixed
- Fixed a broken enum comparison.

## [0.1.1] - 2026-10-28

### Changed
- Bumped `starlette` to 1.3.1.

## [0.1.0] - 2026-10-28

### Added
- Admin panel: initial endpoints for managing datasets and facets.
- Support for enabling/disabling highlighting on specific fields, with or without fragments.

### Changed
- Updated the Dockerfile to use a newer Python version.
- Bumped `anyio` from 4.12.1 to 4.14.2.
- Bumped `urllib3` from 2.6.3 to 2.8.0.
- Bumped `certifi` from 2026.1.4 to 2026.10.18.
- Bumped `starlette` from 0.46.2 to 1.3.1.
- Bumped `pylint` from 3.3.9 to 4.0.9.

### Fixed
- Added missing permissions to a GitHub Actions workflow (code scanning alert fix).

## [0.0.12] - 2026-10-07

### Security
- Hide CMDI editor auth info from the `/datasets` endpoint response.

## [0.0.11] - 2026-09-15

### Added
- Configuration option for the initial expansion level of tree facets.

### Fixed
- Synced range facet property names (`start`, `end`) and fixed sorting for non-range,
  non-histogram, non-date facets.

## [0.0.10] - 2026-06-15

### Added
- `resolve` endpoint to the API, scoped to dataset name.
- `metadata` field on datasets.

### Fixed
- Filtered out `s3_*` items from the `/datasets` list built from the data configuration.

## [0.0.9] - 2026-06-10

### Added
- `GET /datasets` endpoint.
- Configuration option for the initial open/closed state of a facet.

## [0.0.8] - 2026-05-20

### Changed
- CMDI connector updates.

## [0.0.7] - 2026-02-25

### Added
- `config` column to the `detail_properties` collection.
- Histogram highlighter feature.

### Changed
- Bumped `urllib3` from 2.5.0 to 2.6.3.
- Bumped `starlette` from 0.46.2 to 0.49.1.

## [0.0.6] - 2025-12-02

### Added
- Histogram facet support.

## [0.0.5] - 2025-12-02

### Added
- Beta release.

## [0.0.4] - 2025-06-12

### Changed
- Dockerfile adjustments.

## [0.0.3] - 2025-06-11

### Changed
- Docker build adjustments.

## [0.0.2] - 2025-06-02

### Added
- Test version; build Docker image.

## [0.0.1] - 2025-06-02

### Added
- Initial build.
- OpenAPI specification.
- Initial endpoints for searching (see OpenAPI specification).
