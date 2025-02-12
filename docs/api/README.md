# API Documentation

## Overview

The Discord Scammer Defense API provides endpoints for managing scammer detection, moderation, and community features. This RESTful API uses JSON for request and response bodies.

## Base URL

```
https://api.dsd.example.com/v1
```

## Authentication

All API requests require authentication using a Bearer token:

```http
Authorization: Bearer your-api-token
```

## Rate Limiting

- 100 requests per minute per IP
- 1000 requests per hour per token
- Headers include rate limit information

## Endpoints

### Scammer Detection

#### Check User
```http
GET /users/{discord_id}/check
```

Response:
```json
{
  "discord_id": "123456789",
  "is_flagged": true,
  "confidence": 0.95,
  "flags": ["avatar_match", "name_similar"],
  "flagged_at": "2023-05-20T15:30:00Z"
}
```

#### Report User
```http
POST /users/{discord_id}/report
```

Request:
```json
{
  "reason": "avatar_impersonation",
  "evidence": {
    "original_user_id": "987654321",
    "similarity_score": 0.98
  },
  "reporter_id": "456789123"
}
```

### Moderation

#### Get Moderation Actions
```http
GET /servers/{server_id}/actions
```

#### Create Moderation Action
```http
POST /servers/{server_id}/actions
```

Request:
```json
{
  "user_id": "123456789",
  "action_type": "ban",
  "reason": "Confirmed scammer",
  "duration": 3600
}
```

### Appeals

#### Submit Appeal
```http
POST /appeals
```

Request:
```json
{
  "user_id": "123456789",
  "reason": "False positive detection",
  "evidence": "Explanation and links",
  "contact_info": "discord_username#1234"
}
```

#### Get Appeal Status
```http
GET /appeals/{appeal_id}
```

### Rewards

#### Get User Points
```http
GET /users/{discord_id}/points
```

#### Award Points
```http
POST /users/{discord_id}/points
```

Request:
```json
{
  "amount": 100,
  "reason": "Accurate scammer report",
  "reference_id": "report_123"
}
```

## Error Handling

### Error Response Format
```json
{
  "error": {
    "code": "invalid_request",
    "message": "Detailed error message",
    "details": {
      "field": "specific_field",
      "reason": "validation_failed"
    }
  }
}
```

### Common Error Codes

- 400: Bad Request
- 401: Unauthorized
- 403: Forbidden
- 404: Not Found
- 429: Too Many Requests
- 500: Internal Server Error

## Webhooks

### Configuration
```http
POST /webhooks
```

Request:
```json
{
  "url": "https://your-server.com/webhook",
  "events": ["user.flagged", "appeal.created"],
  "secret": "your-webhook-secret"
}
```

### Event Types

- user.flagged
- user.cleared
- appeal.created
- appeal.updated
- points.awarded

## SDK Support

Official SDKs are available for:

- Python
- JavaScript/Node.js
- Java
- Go

## Examples

### JavaScript
```javascript
const DSD = require('dsd-api');
const client = new DSD('your-api-token');

// Check a user
const result = await client.users.check('123456789');
console.log(result.is_flagged);
```

### Python
```python
from dsd_api import DSDClient
client = DSDClient('your-api-token')

# Report a user
response = client.users.report(
    discord_id='123456789',
    reason='avatar_impersonation',
    evidence={'original_user_id': '987654321'}
)
```

## Best Practices

1. Error Handling
   - Always handle API errors gracefully
   - Implement exponential backoff for retries
   - Log API errors for debugging

2. Rate Limiting
   - Monitor rate limit headers
   - Implement rate limit handling
   - Cache responses when appropriate

3. Security
   - Store API tokens securely
   - Use HTTPS for all requests
   - Validate webhook signatures

4. Performance
   - Batch requests when possible
   - Use pagination for large datasets
   - Implement caching strategies

## Support

- API Status: https://status.dsd.example.com
- Documentation: https://docs.dsd.example.com
- Support Email: irchris5@gmail.com
- Discord Server: https://discord.gg/dsd-dev