# BotForge API Reference

Base URL: `http://localhost:8000/api`

## Authentication

### POST /auth/signup
Create a new user account and organization.

```json
{
  "email": "user@example.com",
  "password": "securepass",
  "full_name": "John Doe",
  "org_name": "My Company"
}
```

### POST /auth/login
```json
{ "email": "user@example.com", "password": "securepass" }
```

### GET /auth/me
Returns current user profile. Requires `Authorization: Bearer <token>`.

## Bots

### GET /bots/
List all bots for the authenticated user's organization.

### POST /bots/
Create a new bot.
```json
{ "name": "Support Bot", "tone": "friendly" }
```

### GET /bots/{id}
### PUT /bots/{id}
### DELETE /bots/{id}
### PATCH /bots/{id}/toggle

## Knowledge Base

### GET /bots/{id}/docs
### POST /bots/{id}/docs/upload (multipart/form-data)
### POST /bots/{id}/docs/url
```json
{ "url": "https://example.com/faq", "name": "FAQ Page" }
```
### DELETE /bots/{id}/docs/{doc_id}
### POST /bots/{id}/docs/reindex
### GET /bots/{id}/docs/chunks

## Chat

### POST /chat/
Send a message and get AI response.
```json
{
  "bot_id": "uuid",
  "message": "What's your return policy?",
  "channel": "website"
}
```

### WebSocket /ws/chat/{conversation_id}
Real-time chat connection.

### POST /chat/feedback
```json
{ "message_id": "uuid", "rating": "thumbs_up" }
```

## Conversations

### GET /conversations/
### GET /conversations/{id}
### PATCH /conversations/{id}/assign?agent_id=uuid
### PATCH /conversations/{id}/resolve
### PATCH /conversations/{id}/handoff
### POST /conversations/{id}/reply
### GET /conversations/{id}/suggest

## Analytics

### GET /analytics/overview?bot_id=uuid&range=7d
### GET /analytics/top-questions?bot_id=uuid
### GET /analytics/unanswered?bot_id=uuid
### GET /analytics/channels?bot_id=uuid
### GET /analytics/export?bot_id=uuid&format=json

## Widget

### GET /widget/{bot_id}/config
### PUT /widget/{bot_id}/config
### GET /widget/{bot_id}/embed

## Settings

### GET/PUT /settings/org
### GET/POST /settings/team
### GET/POST /settings/webhooks
### GET/POST /settings/api-keys

## Channel Webhooks

### GET/POST /channels/whatsapp/webhook
### GET/POST /channels/instagram/webhook
### POST /channels/slack/events
### POST /channels/email/reply
