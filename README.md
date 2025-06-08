# Notion Synch

This project provides a small Flask service that converts Notion calendar data to ICS format.

## Environment Variables

- `NOTION_API_KEY`: Token for accessing the Notion API.
- `DATABASE_ID`: ID of the Notion database to read events from.
- `PORT`: Port the Flask application runs on (default: `5004`).
- `NGROK_AUTH_TOKEN`: Authentication token used by Ngrok to create secure tunnels. When using Ngrok, export this variable so the value can be injected into `ngrok.yml`.

## Ngrok

The `ngrok.yml` file contains Ngrok configuration and should not be committed with your secret token. The file is included in `.gitignore`. When running Ngrok you can supply your token via the `NGROK_AUTH_TOKEN` environment variable.
