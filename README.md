# Jellyfin Webhook Processor for Streamyfin

This project is a smart webhook processor designed to work with [Jellyfin](https://jellyfin.org/) and [Streamyfin](https://github.com/streamyfin/streamyfin) with the [Companion plugin](https://github.com/streamyfin/jellyfin-plugin-streamyfin). It allows you to filter, group, and forward notifications from Jellyfin to Streamyfin, making your notification flow more relevant and user-friendly.

## Features

- **Receives notifications** from Jellyfin (or any compatible webhook source).
- **Buffers notifications** for a configurable period to avoid spamming Streamyfin.
- **Filters and groups notifications**: If several similar notifications (e.g. new episodes) arrive in a short time, it can group them and send a single, custom notification to Streamyfin.
- **Customizes notification content**: You can define the message template and how the season number is extracted.
- **Threshold logic**: If the number of notifications in the buffer exceeds a threshold, a single grouped notification is sent. Otherwise, all notifications are forwarded as-is.

## Use case

This processor is ideal for users who want to:
- Avoid being spammed by multiple notifications when several episodes are added at once.
- Have a clean, readable notification in Streamyfin, especially for new seasons or grouped releases.
- Customize the notification message and logic easily via environment variables.

## How to use

### 1. Install and configure [jellyfin-plugin-streamyfin](https://github.com/streamyfin/jellyfin-plugin-streamyfin/tree/main)

Install the webhook plugin and the jellyfin-plugin-streamyfin on your Jellyfin instance.
Follow the tutorial on the [Github repository](https://github.com/streamyfin/jellyfin-plugin-streamyfin/blob/main/NOTIFICATIONS.md)

### 2. Create a new or copy the following in your docker-compose.yml

```bash
services:
  jellyfin_webhook_processor:
    image: wassax7/jellyfin-webhook-processor-streamyfin:latest
    container_name: jellyfin_webhook_processor
    environment:
      - WEBHOOK_URL=https://mydomain.com//Streamyfin/notification
      - HEADER_AUTHORIZATION=MediaBrowser Token=""
      - THRESHOLD=5
      - BUFFER_TIME=20
      - SIMILARITY_PREFIX=New episode
      - CUSTOM_BODY_TEMPLATE=New episodes of Season {season} available for {title}
      - SEASON_KEYWORD=Season
    ports:
      - "8000:8000"
    restart: unless-stopped
```

### 3. Configure environment variables

Edit the `docker-compose.yml` file to set the following variables:

- `WEBHOOK_URL`: The Streamyfin notification endpoint (e.g. `https://mydomain.com/Streamyfin/notification`)
- `HEADER_AUTHORIZATION`: Authorization header for Streamyfin ([Tutorial here](https://github.com/streamyfin/jellyfin-plugin-streamyfin/blob/main/NOTIFICATIONS.md#endpoint-authorization-required))
- `SIMILARITY_PREFIX`: The prefix to look for in notification bodies (e.g. `New episode`)
- `THRESHOLD`: Minimum number of notifications in the buffer to trigger grouping (default: 5)
- `BUFFER_TIME`: Buffering time in seconds (default: 20)
- `CUSTOM_BODY_TEMPLATE`: Template for the grouped notification (e.g. `New episodes of Season {season} available for {title}`)
- `SEASON_KEYWORD`: The keyword to extract the season number (e.g. `Season` or `season`)

Example:
```yaml
      - WEBHOOK_URL=https://mydomain.com/Streamyfin/notification
      - HEADER_AUTHORIZATION=MediaBrowser Token="..."
      - SIMILARITY_PREFIX=New episode
      - THRESHOLD=5
      - BUFFER_TIME=20
      - CUSTOM_BODY_TEMPLATE=New episodes of Season {season} available for {title}
      - SEASON_KEYWORD=Season
```

### 3. Run the service

```bash
docker compose up -d
```

The service will listen on port 8000 by default.
Configure Jellyfin to send webhooks to `http(s)://<your-server>:8000/`.

## How it works

- When a notification is received, it is added to a buffer.
- The buffer timer is reset with each new notification.
- After `BUFFER_TIME` seconds without new notifications, the buffer is processed:
  - If the buffer contains more than `THRESHOLD` notifications with the prefix, a single grouped notification is sent to Streamyfin (using your custom template).
  - If not, all notifications with the prefix are sent as-is.
  - All notifications without the prefix are always sent as-is.

## Advanced

- The season number is extracted from the notification body using the `SEASON_KEYWORD` (e.g. it will match `Saison 03` or `Season 2`).
- You can fully customize the grouped notification message with the `CUSTOM_BODY_TEMPLATE` variable.

## License

MIT
