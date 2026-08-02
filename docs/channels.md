# Channel Setup Guide

## Website Widget

1. Go to Bot Builder > Channels tab
2. Enable "Website Widget"
3. Copy the embed code
4. Paste before `</body>` in your website HTML:
```html
<script src="https://api.botforge.app/widget.js" data-bot-id="YOUR_BOT_ID"></script>
```

## WhatsApp

1. Create a Meta Business account at business.facebook.com
2. Set up WhatsApp Business API
3. Get your access token and phone number ID
4. Add to `.env`:
   - `WHATSAPP_TOKEN`
   - `WHATSAPP_VERIFY_TOKEN`
   - `WHATSAPP_PHONE_NUMBER_ID`
5. Set webhook URL: `https://api.botforge.app/api/channels/whatsapp/webhook`
6. Subscribe to `messages` webhook field

## Instagram

1. Create a Facebook App at developers.facebook.com
2. Add Instagram Basic Display API
3. Connect your Instagram Business account
4. Set webhook URL: `https://api.botforge.app/api/channels/instagram/webhook`
5. Subscribe to `messages` webhook field

## Slack

1. Create a Slack App at api.slack.com/apps
2. Enable Event Subscriptions
3. Set Request URL: `https://api.botforge.app/api/channels/slack/events`
4. Subscribe to `message.im` event
5. Install app to workspace
6. Add bot token to `.env`: `SLACK_BOT_TOKEN`

## Email

1. Enable IMAP on your email provider (Gmail: Settings > IMAP)
2. Generate an app password (Gmail: Security > App Passwords)
3. Add to `.env`:
   - `EMAIL_IMAP_HOST`, `EMAIL_SMTP_HOST`
   - `EMAIL_ADDRESS`, `EMAIL_PASSWORD`
4. Celery Beat checks inbox every 60 seconds
