# API Dokumentasjon

## Oversikt

OSINT Email Investigator API er bygget med FastAPI og tilbyr en RESTful interface for e-postetterforskning og validering.

## Base URL

```
https://api.yourdomain.com/api/v1
```

## Autentisering

API-et bruker JWT Bearer tokens for autentisering.

```bash
curl -H "Authorization: Bearer <your_token>" https://api.yourdomain.com/api/v1/contacts
```

## Endepunkter

### Autentisering

#### Login

```http
POST /auth/token

{
    "username": "string",
    "password": "string"
}
```

Response:
```json
{
    "access_token": "string",
    "token_type": "bearer"
}
```

### Contacts

#### Hent Kontakter

```http
GET /contacts

Query Parameters:
- status: string (optional)
- domain: string (optional)
- limit: integer (default: 100)
- offset: integer (default: 0)
```

Response:
```json
{
    "items": [
        {
            "email": "string",
            "domain": "string",
            "name": "string",
            "role": "string",
            "company": "string",
            "status": "string",
            "confidence_score": number
        }
    ],
    "total": integer,
    "limit": integer,
    "offset": integer
}
```

#### Opprett Kontakt

```http
POST /contacts

{
    "email": "string",
    "domain": "string",
    "name": "string",
    "role": "string",
    "company": "string"
}
```

#### Oppdater Kontaktstatus

```http
PUT /contacts/{email}/status

{
    "status": "string"
}
```

### Export

#### Eksporter Kontakter

```http
POST /export

{
    "min_score": number,
    "format": "csv" | "json"
}
```

### Statistics

#### Hent Statistikk

```http
GET /stats
```

Response:
```json
{
    "total_contacts": integer,
    "validated_contacts": integer,
    "success_rate": number,
    "average_score": number
}
```

## Feilhåndtering

API-et returnerer standardiserte feilresponser:

```json
{
    "status": integer,
    "message": "string",
    "details": object
}
```

### HTTP Status Koder

- 200: Success
- 201: Created
- 400: Bad Request
- 401: Unauthorized
- 403: Forbidden
- 404: Not Found
- 429: Too Many Requests
- 500: Internal Server Error

## Rate Limiting

API-et har følgende rate limits:

- 100 requests per minutt for autentiserte brukere
- 10 requests per minutt for uautentiserte brukere

## Websocket API

### Real-time Updates

```javascript
const ws = new WebSocket('wss://api.yourdomain.com/ws');

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log('Received:', data);
};
```

## Eksempler

### Python

```python
import requests

API_URL = "https://api.yourdomain.com/api/v1"
TOKEN = "your_token"

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

# Hent kontakter
response = requests.get(f"{API_URL}/contacts", headers=headers)
contacts = response.json()

# Eksporter data
export_params = {
    "min_score": 0.7,
    "format": "csv"
}
response = requests.post(f"{API_URL}/export", json=export_params, headers=headers)
```

### JavaScript

```javascript
const API_URL = 'https://api.yourdomain.com/api/v1';
const TOKEN = 'your_token';

const headers = {
    'Authorization': `Bearer ${TOKEN}`,
    'Content-Type': 'application/json'
};

// Hent kontakter
async function getContacts() {
    const response = await fetch(`${API_URL}/contacts`, { headers });
    return await response.json();
}

// Eksporter data
async function exportContacts() {
    const params = {
        min_score: 0.7,
        format: 'csv'
    };
    
    const response = await fetch(`${API_URL}/export`, {
        method: 'POST',
        headers,
        body: JSON.stringify(params)
    });
    
    return await response.json();
}
```

## Changelog

### v1.0.0 (2025-11-10)
- Initial API release
- Basic CRUD operations
- Authentication
- Export functionality

### v1.1.0 (Planlagt)
- Batch operations
- Advanced filtering
- Real-time notifications
- Enhanced export options