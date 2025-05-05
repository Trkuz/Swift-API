# Swift-API

A RESTful API for SWIFT codes operations with automatic headquarters-branch relationship handling.

## Overview

This API utilizes the FastAPI framework and provides a comprehensive backend for managing SWIFT codes. Application comes with the PostgreSQL database, populated with SWIFT data making it ready to use.

### Features

- **Automatic relationship management** between headquarters and branches
- **PostgreSQL database** with SQLAlchemy ORM
- **Validation** using Pydantic models
- **Alembic migrations** for database version control
- **Unit and Integration tests** using pytest

## API Endpoints

- `GET /v1/swift-codes/{swift_code}` - Retrieves details for a specified SWIFT code
- `GET /v1/swift-codes/country/{country_iso2}` - Retrieves all SWIFT code details for specified country
- `POST /v1/swift-codes` - Adds a new SWIFT entry
- `DELETE /v1/swift-codes/{swift_code}` - Deletes a SWIFT entry

## Getting Started

### Prerequisites

- [Docker](https://www.docker.com/products/docker-desktop)
- [Docker Compose](https://docs.docker.com/compose/install/)

### Running the Application

Application can be run using Docker:

1. Clone the repository:
   ```bash
   git clone https://github.com/Trkuz/Swift-API.git
   cd Swift-API
   ```

2. Run the application with Docker Compose:
   ```bash
   docker-compose up -d
   ```


After building has finished building, user can access documentation via:
   - Swagger UI: http://localhost:8080/docs
   - ReDoc: http://localhost:8080/redoc

## Project Structure

```
Swift-API/
├── Database/                     # Database code
│   ├── db_config/                # Alembic configuration
│   ├── utilities/                # Database utilities
│   └── db_models.py              # SQLAlchemy models
├── Models/                       # Pydantic models
├── data/                         # Data files
├── tests/                        # Test suite
├── Dockerfile                    # Docker configuration
├── docker-compose.yml            # Docker Compose configuration
├── main.py                       # FastAPI routes
└── populate_base.py              # Database population script
```

## Running Tests

Application test can be run by executing:
```bash
docker-compose run api pytest -v
```

