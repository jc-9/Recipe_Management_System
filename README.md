# Recipe Management System

This project aims to provide a centralized system for managing and distributing controlled versions of recipe books to factory stations using Dockerized microservices.

## Getting Started

Follow the step-by-step instructions to set up your local development environment.

### Prerequisites

* [Docker Desktop](https://www.docker.com/products/docker-desktop/) (or Docker Engine and Docker Compose)
* Python 3.12.9
* pip

### Setup Infrastructure Services

1.  Ensure Docker is running.
2.  Navigate to the root of this project:
    `cd recipe-management-system`
3.  Bring up the core infrastructure services (PostgreSQL, pgAdmin, MinIO) defined in `docker-compose.yml`:
    `docker compose up -d`

## Services Overview

* **PostgreSQL (`db`):** Your primary database for structured recipe metadata. Note these are only defaults and may be different durring implementation. I need to come back and upate these as needed
    * Access via: `db:5432` from other containers
    * Managed via `pgAdmin` web UI.
* **pgAdmin (`pgadmin`):** Web UI for PostgreSQL.
    * Access via: `http://localhost:5050`
    * Login: `pgadmin@example.com` / `admin` (or as configured in `docker-compose.yml`)
* **MinIO (`minio`):** Object storage for recipe binary files.
    * Access via: `http://localhost:9000` (API)
    * Console: `http://localhost:9001`
    * Login: `minioadmin` / `minioadmin` (or as configured in `docker-compose.yml`)

---
*More instructions will be added here as the project progresses.*