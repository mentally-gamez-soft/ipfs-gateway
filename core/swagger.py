"""
Swagger/OpenAPI Configuration for IPFS Gateway API

Provides centralized OpenAPI specification and Flasgger configuration
for interactive API documentation (Swagger UI).
"""

from flasgger import Flasgger

# OpenAPI 3.0 specification template
SWAGGER_TEMPLATE = {
    "swagger": "2.0",
    "info": {
        "title": "IPFS Gateway API",
        "description": "RESTful API for accessing and managing content on the InterPlanetary File System (IPFS) network.",
        "version": "1.0.0",
        "contact": {
            "name": "API Support",
            "url": "https://github.com/ipfs-gateway",
        },
        "license": {
            "name": "MIT",
        },
    },
    "host": "localhost:5000",
    "basePath": "/",
    "schemes": ["http", "https"],
    "consumes": ["application/json", "multipart/form-data"],
    "produces": ["application/json"],
    "definitions": {
        "User": {
            "type": "object",
            "properties": {
                "id": {"type": "integer", "example": 1},
                "email": {"type": "string", "example": "user@example.com"},
                "status": {
                    "type": "string",
                    "enum": ["active", "inactive"],
                    "example": "active",
                },
                "role": {
                    "type": "string",
                    "enum": ["user", "admin"],
                    "example": "user",
                },
                "created_at": {"type": "string", "format": "date-time"},
                "updated_at": {"type": "string", "format": "date-time"},
            },
        },
        "File": {
            "type": "object",
            "properties": {
                "id": {"type": "integer", "example": 1},
                "user_id": {"type": "integer", "example": 1},
                "cid": {
                    "type": "string",
                    "example": "QmXxxx...",
                    "description": "Content Identifier from IPFS network",
                },
                "filename": {"type": "string", "example": "document.pdf"},
                "file_size": {"type": "integer", "example": 1024000},
                "mime_type": {"type": "string", "example": "application/pdf"},
                "is_pinned": {"type": "boolean", "example": True},
                "created_at": {"type": "string", "format": "date-time"},
                "updated_at": {"type": "string", "format": "date-time"},
            },
        },
        "Error": {
            "type": "object",
            "properties": {
                "error": {"type": "string", "example": "Bad Request"},
                "message": {"type": "string", "example": "Invalid request"},
                "status": {"type": "integer", "example": 400},
            },
        },
        "HealthResponse": {
            "type": "object",
            "properties": {
                "status": {"type": "string", "enum": ["healthy", "unhealthy"]},
                "environment": {"type": "string", "example": "staging"},
                "timestamp": {"type": "string", "format": "date-time"},
            },
        },
    },
    "securityDefinitions": {
        "ApiKeyAuth": {
            "type": "apiKey",
            "in": "header",
            "name": "X-API-Key",
            "description": "API key authentication",
        }
    },
    "security": [{"ApiKeyAuth": []}],
}

# Flasgger configuration
SWAGGER_CONFIG = {
    "headers": [],
    "specs": [
        {
            "endpoint": "apispec",
            "route": "/apispec.json",
            "rule_filter": lambda rule: True,
            "model_filter": lambda tag: True,
        }
    ],
    "static_url_path": "/flasgger_static",
    "swagger_ui": True,
    "specs_route": "/api/docs",
    "title": "IPFS Gateway API",
    "uiversion": 3,
}


def init_swagger(app, env: str = "development"):
    """
    Initialize Flasgger (Swagger UI) for the Flask app.

    Args:
        app: Flask application instance
        env: Environment (development, staging, production)

    Only enables Swagger UI in development and staging environments.
    Production should serve API docs through separate secure endpoint if needed.
    """
    if env not in ["development", "staging"]:
        return

    # Update host based on environment
    if env == "staging":
        SWAGGER_TEMPLATE["host"] = "ipfs-gateway-staging.nw.r.appspot.com"
        SWAGGER_TEMPLATE["schemes"] = ["https"]
    elif env == "development":
        SWAGGER_TEMPLATE["host"] = "localhost:5000"
        SWAGGER_TEMPLATE["schemes"] = ["http", "https"]

    swagger = Flasgger(
        app,
        template=SWAGGER_TEMPLATE,
        config=SWAGGER_CONFIG,
    )

    return swagger


# Endpoint documentation decorators
AUTH_REGISTER_DOCS = {
    "tags": ["Authentication"],
    "summary": "Register a new user and receive an API key",
    "parameters": [
        {
            "name": "body",
            "in": "body",
            "required": True,
            "schema": {
                "type": "object",
                "properties": {
                    "email": {"type": "string", "example": "user@example.com"}
                },
                "required": ["email"],
            },
        }
    ],
    "responses": {
        201: {
            "description": "User registered successfully",
            "schema": {
                "type": "object",
                "properties": {
                    "api_key": {"type": "string"},
                    "user_id": {"type": "integer"},
                    "email": {"type": "string"},
                },
            },
        },
        400: {"description": "Invalid email format", "schema": {"$ref": "#/definitions/Error"}},
        409: {
            "description": "User already exists",
            "schema": {"$ref": "#/definitions/Error"},
        },
    },
}

AUTH_STATUS_DOCS = {
    "tags": ["Authentication"],
    "summary": "Check user status",
    "security": [{"ApiKeyAuth": []}],
    "responses": {
        200: {
            "description": "User status retrieved",
            "schema": {"$ref": "#/definitions/User"},
        },
        401: {
            "description": "Invalid or missing API key",
            "schema": {"$ref": "#/definitions/Error"},
        },
    },
}

UPLOAD_DOCS = {
    "tags": ["Content Management"],
    "summary": "Upload a file to IPFS network",
    "security": [{"ApiKeyAuth": []}],
    "parameters": [
        {
            "name": "file",
            "in": "formData",
            "type": "file",
            "required": True,
            "description": "File to upload (PDF, PNG, etc.)",
        }
    ],
    "responses": {
        201: {
            "description": "File uploaded successfully",
            "schema": {
                "type": "object",
                "properties": {
                    "cid": {"type": "string", "example": "QmXxxx..."},
                    "filename": {"type": "string"},
                    "file_size": {"type": "integer"},
                    "mime_type": {"type": "string"},
                    "message": {"type": "string"},
                },
            },
        },
        400: {
            "description": "Invalid file or missing file",
            "schema": {"$ref": "#/definitions/Error"},
        },
        401: {"description": "Unauthorized", "schema": {"$ref": "#/definitions/Error"}},
        413: {
            "description": "File too large (exceeds quota)",
            "schema": {"$ref": "#/definitions/Error"},
        },
    },
}

RETRIEVE_DOCS = {
    "tags": ["Content Management"],
    "summary": "Retrieve a file from IPFS network",
    "security": [{"ApiKeyAuth": []}],
    "parameters": [
        {
            "name": "cid",
            "in": "path",
            "type": "string",
            "required": True,
            "description": "Content Identifier (CID) of the file",
        }
    ],
    "responses": {
        200: {
            "description": "File content retrieved",
            "schema": {
                "type": "object",
                "properties": {
                    "content": {"type": "string", "format": "byte"},
                    "filename": {"type": "string"},
                    "mime_type": {"type": "string"},
                },
            },
        },
        401: {"description": "Unauthorized", "schema": {"$ref": "#/definitions/Error"}},
        403: {
            "description": "Access denied (not file owner)",
            "schema": {"$ref": "#/definitions/Error"},
        },
        404: {
            "description": "File not found",
            "schema": {"$ref": "#/definitions/Error"},
        },
    },
}

PIN_DOCS = {
    "tags": ["Content Pinning"],
    "summary": "Pin content to ensure availability on IPFS",
    "security": [{"ApiKeyAuth": []}],
    "parameters": [
        {
            "name": "cid",
            "in": "path",
            "type": "string",
            "required": True,
            "description": "Content Identifier (CID) to pin",
        }
    ],
    "responses": {
        200: {
            "description": "Content pinned successfully",
            "schema": {
                "type": "object",
                "properties": {
                    "cid": {"type": "string"},
                    "is_pinned": {"type": "boolean", "example": True},
                    "message": {"type": "string"},
                },
            },
        },
        401: {"description": "Unauthorized", "schema": {"$ref": "#/definitions/Error"}},
        404: {
            "description": "File not found",
            "schema": {"$ref": "#/definitions/Error"},
        },
    },
}

UNPIN_DOCS = {
    "tags": ["Content Pinning"],
    "summary": "Unpin content from IPFS network",
    "security": [{"ApiKeyAuth": []}],
    "parameters": [
        {
            "name": "cid",
            "in": "path",
            "type": "string",
            "required": True,
            "description": "Content Identifier (CID) to unpin",
        }
    ],
    "responses": {
        200: {
            "description": "Content unpinned successfully",
            "schema": {
                "type": "object",
                "properties": {
                    "cid": {"type": "string"},
                    "is_pinned": {"type": "boolean", "example": False},
                    "message": {"type": "string"},
                },
            },
        },
        401: {"description": "Unauthorized", "schema": {"$ref": "#/definitions/Error"}},
        404: {
            "description": "File not found",
            "schema": {"$ref": "#/definitions/Error"},
        },
    },
}

HEALTH_DOCS = {
    "tags": ["Health"],
    "summary": "Check API health status",
    "responses": {
        200: {
            "description": "API is healthy",
            "schema": {"$ref": "#/definitions/HealthResponse"},
        },
        503: {
            "description": "API is unhealthy",
            "schema": {"$ref": "#/definitions/HealthResponse"},
        },
    },
}

DB_CHECK_DOCS = {
    "tags": ["Health"],
    "summary": "Check database connectivity",
    "responses": {
        200: {
            "description": "Database is reachable",
            "schema": {
                "type": "object",
                "properties": {
                    "status": {"type": "string", "enum": ["ok"]},
                    "database": {"type": "string"},
                    "query_result": {"type": "integer", "example": 1},
                },
            },
        },
        503: {
            "description": "Database is unreachable",
            "schema": {
                "type": "object",
                "properties": {
                    "status": {"type": "string", "enum": ["error"]},
                    "database": {"type": "string"},
                    "error": {"type": "string"},
                },
            },
        },
    },
}
