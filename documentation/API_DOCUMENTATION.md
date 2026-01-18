# API Documentation - IPFS Gateway

**Last Updated**: January 18, 2026  
**API Version**: 1.0.0  
**Status**: Live (Staging)

## Quick Links

- **Swagger UI** (Dev/Staging only): `/api/docs`
- **OpenAPI Spec (JSON)**: `/apispec.json`
- **Postman Collection**: See [IPFS_Gateway_API.postman_collection.json](./IPFS_Gateway_API.postman_collection.json)

## Table of Contents

1. [Overview](#overview)
2. [Authentication](#authentication)
3. [Base URLs](#base-urls)
4. [API Endpoints](#api-endpoints)
5. [Error Handling](#error-handling)
6. [Examples](#examples)
7. [Postman Setup](#postman-setup)

---

## Overview

The IPFS Gateway API provides a RESTful interface for interacting with the InterPlanetary File System (IPFS). Users can upload files, retrieve content, manage pinning, and access their account information.

### Key Features

- **Content Upload & Retrieval**: Upload files to IPFS and retrieve them using Content Identifiers (CIDs)
- **Content Pinning**: Pin/unpin content to ensure lifetime availability on IPFS
- **User Management**: Register, authenticate, and manage user accounts
- **Comprehensive Logging**: All API requests and responses are logged for audit trails
- **Health Checks**: Built-in health endpoints for monitoring

---

## Authentication

### API Key Authentication

All endpoints except `/register`, `/renew`, and `/health` require an API key via the `X-API-Key` header.

```bash
curl -H "X-API-Key: your-api-key" http://localhost:5000/status
```

### Getting Your API Key

1. **Register**: `POST /register` with your email
2. **Response**: Receive your unique API key
3. **Use**: Include `X-API-Key: {api_key}` in all subsequent requests

### Admin Authentication

Admin endpoints (`/revoke`, `/reactivate`) require an admin API key.

---

## Base URLs

| Environment | URL | Swagger UI | Notes |
|-------------|-----|-----------|-------|
| Development | `http://localhost:5000` | ✓ `/api/docs` | Local development |
| Staging | `https://ipfs-gateway-staging.nw.r.appspot.com` | ✓ `/api/docs` | Pre-production testing |
| Production | TBD | ✗ | Docs not exposed |

---

## API Endpoints

### Authentication Endpoints

#### POST /register
Register a new user and receive an API key.

**Request:**
```json
{
  "email": "user@example.com"
}
```

**Response (201 Created):**
```json
{
  "email": "user@example.com",
  "api_key": "sk_live_xxxxxxxxxxxx"
}
```

**Error Responses:**
- `400`: Missing email field
- `409`: User already exists with this email

---

#### POST /status
Check current user status and information.

**Headers:**
```
X-API-Key: sk_live_xxxxxxxxxxxx
```

**Response (200 OK):**
```json
{
  "id": 1,
  "email": "user@example.com",
  "status": "active",
  "role": "user",
  "created_at": "2026-01-18T10:00:00Z",
  "updated_at": "2026-01-18T10:00:00Z"
}
```

**Error Responses:**
- `401`: Invalid or missing API key

---

#### POST /renew
Renew your API key.

**Request:**
```json
{
  "email": "user@example.com"
}
```

**Response (200 OK):**
```json
{
  "email": "user@example.com",
  "api_key": "sk_live_newapikey"
}
```

---

#### POST /revoke (Admin)
Revoke/deactivate a user account.

**Headers:**
```
X-API-Key: admin-api-key
```

**Request:**
```json
{
  "email": "user@example.com"
}
```

**Response (200 OK):**
```json
{
  "status": "revoked"
}
```

---

#### POST /reactivate (Admin)
Reactivate a revoked user account.

**Headers:**
```
X-API-Key: admin-api-key
```

**Request:**
```json
{
  "email": "user@example.com"
}
```

**Response (200 OK):**
```json
{
  "status": "active"
}
```

---

### Content Management Endpoints

#### POST /upload
Upload a file to IPFS network.

**Headers:**
```
X-API-Key: sk_live_xxxxxxxxxxxx
Content-Type: multipart/form-data
```

**Form Data:**
- `file` (required): File to upload

**Response (201 Created):**
```json
{
  "cid": "QmXxxxxxxxxxxxxxxxxxxxx",
  "filename": "document.pdf",
  "file_size": 102400,
  "mime_type": "application/pdf",
  "message": "File uploaded successfully"
}
```

**Error Responses:**
- `400`: Missing file or invalid file
- `401`: Unauthorized (invalid/missing API key)
- `413`: File too large (exceeds user quota)

---

#### GET /retrieve/{cid}
Retrieve a file from IPFS network.

**URL Parameters:**
- `cid` (required): Content Identifier of the file

**Headers:**
```
X-API-Key: sk_live_xxxxxxxxxxxx
```

**Response (200 OK):**
- Returns file binary content
- Response headers include:
  - `Content-Type`: MIME type of file
  - `Content-Disposition`: Filename

**Error Responses:**
- `401`: Unauthorized
- `403`: Access denied (not file owner)
- `404`: File not found

---

### Content Pinning Endpoints

#### POST /pin/{cid}
Pin content to ensure lifetime availability on IPFS.

**URL Parameters:**
- `cid` (required): Content Identifier to pin

**Headers:**
```
X-API-Key: sk_live_xxxxxxxxxxxx
```

**Response (200 OK):**
```json
{
  "cid": "QmXxxxxxxxxxxxxxxxxxxxx",
  "is_pinned": true,
  "message": "Content pinned successfully"
}
```

**Error Responses:**
- `401`: Unauthorized
- `404`: File/CID not found

---

#### POST /unpin/{cid}
Unpin content from IPFS network.

**URL Parameters:**
- `cid` (required): Content Identifier to unpin

**Headers:**
```
X-API-Key: sk_live_xxxxxxxxxxxx
```

**Response (200 OK):**
```json
{
  "cid": "QmXxxxxxxxxxxxxxxxxxxxx",
  "is_pinned": false,
  "message": "Content unpinned successfully"
}
```

**Error Responses:**
- `401`: Unauthorized
- `404`: File/CID not found

---

### Health & Status Endpoints

#### GET /health
Check API health status (no authentication required).

**Response (200 OK):**
```json
{
  "status": "ok",
  "app": "ipfs-gateway",
  "env": "staging"
}
```

---

#### GET /db-check
Verify database connectivity (no authentication required).

**Response (200 OK):**
```json
{
  "status": "ok",
  "database": "connected",
  "query_result": 1
}
```

**Response (503 Service Unavailable):**
```json
{
  "status": "error",
  "error": "Connection timeout"
}
```

---

## Error Handling

All errors follow a consistent format:

```json
{
  "error": "Error Type",
  "message": "Detailed error message",
  "status": 400
}
```

### Common HTTP Status Codes

| Status | Meaning | Typical Cause |
|--------|---------|---------------|
| 200 | OK | Successful request |
| 201 | Created | Resource successfully created |
| 400 | Bad Request | Missing/invalid parameters |
| 401 | Unauthorized | Missing or invalid API key |
| 403 | Forbidden | Insufficient permissions |
| 404 | Not Found | Resource doesn't exist |
| 409 | Conflict | Resource already exists |
| 413 | Payload Too Large | File exceeds size limit |
| 500 | Internal Server Error | Server-side error |
| 503 | Service Unavailable | Database or service down |

---

## Examples

### Complete Workflow Example

#### 1. Register User
```bash
curl -X POST http://localhost:5000/register \
  -H "Content-Type: application/json" \
  -d '{"email": "alice@example.com"}'
```

Response:
```json
{
  "email": "alice@example.com",
  "api_key": "sk_live_abc123xyz"
}
```

#### 2. Upload File
```bash
curl -X POST http://localhost:5000/upload \
  -H "X-API-Key: sk_live_abc123xyz" \
  -F "file=@document.pdf"
```

Response:
```json
{
  "cid": "QmAbCdEfGhIjKlMnOpQrStUvWxYz",
  "filename": "document.pdf",
  "file_size": 102400,
  "mime_type": "application/pdf"
}
```

#### 3. Pin Content
```bash
curl -X POST http://localhost:5000/pin/QmAbCdEfGhIjKlMnOpQrStUvWxYz \
  -H "X-API-Key: sk_live_abc123xyz"
```

Response:
```json
{
  "cid": "QmAbCdEfGhIjKlMnOpQrStUvWxYz",
  "is_pinned": true,
  "message": "Content pinned successfully"
}
```

#### 4. Retrieve File
```bash
curl -X GET http://localhost:5000/retrieve/QmAbCdEfGhIjKlMnOpQrStUvWxYz \
  -H "X-API-Key: sk_live_abc123xyz" \
  -o downloaded_file.pdf
```

#### 5. Check Status
```bash
curl -X POST http://localhost:5000/status \
  -H "X-API-Key: sk_live_abc123xyz"
```

Response:
```json
{
  "id": 1,
  "email": "alice@example.com",
  "status": "active",
  "role": "user"
}
```

---

## Postman Setup

### Import the Collection

1. **Download** [IPFS_Gateway_API.postman_collection.json](./IPFS_Gateway_API.postman_collection.json)
2. **Open Postman**
3. **Import**: `File > Import` or drag & drop the JSON file
4. **Select**: Choose "Postman Collection" format

### Configure Variables

The collection uses environment variables. Set these in Postman:

**Environment Variables:**

| Variable | Development | Staging | Notes |
|----------|-------------|---------|-------|
| `base_url` | `http://localhost:5000` | `https://ipfs-gateway-staging.nw.r.appspot.com` | API base URL |
| `api_key` | Your API key | Your API key | Get from /register endpoint |
| `admin_api_key` | Admin key | Admin key | For admin endpoints |
| `cid` | Upload a file first | Upload a file first | Content Identifier |

### Steps to Use

1. **Register a User**
   - Go to `Authentication > Register User`
   - Send request
   - Copy `api_key` from response
   - Set `api_key` variable in Postman

2. **Upload a File**
   - Go to `Content Management > Upload File`
   - Click "Select Files" in the request body
   - Send request
   - Copy `cid` from response
   - Set `cid` variable in Postman

3. **Explore Endpoints**
   - Use other pre-configured requests
   - Variables are automatically substituted

---

## Rate Limiting

Currently, no rate limiting is enforced. Fair usage is expected.

---

## Support & Contact

For issues, feature requests, or questions:
- GitHub: [ipfs-gateway](https://github.com/ipfs-gateway)
- Email: support@example.com

---

## Version History

- **v1.0** (January 18, 2026): Initial API release with Swagger UI and Postman collection
