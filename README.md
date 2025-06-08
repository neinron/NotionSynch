# NotionSynch

This project provides a small Flask application that converts events from a Notion database into an iCalendar (`.ics`) feed.

## Setup

1. **Clone the repository**
   ```bash
   git clone <repo-url>
   cd NotionSynch
   ```

2. **Create a virtual environment and install dependencies**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Configure environment variables**

   The application reads its configuration from environment variables. Create a `.env` file in the project root or export the variables in your shell.

   Required variables:
   - `NOTION_API_KEY` – your Notion integration token.
   - `DATABASE_ID` – the ID of the Notion database to read events from.

   Optional variables:
   - `PORT` – port to run the Flask app on (defaults to `5004`).

   Example `.env` file:
   ```env
   NOTION_API_KEY=secret_...
   DATABASE_ID=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   PORT=5004
   ```

4. **Run the application**

   ```bash
   python notion_to_ics.py
   ```

   The app will start and listen on `0.0.0.0:$PORT`. You can then fetch your calendar feed from `http://localhost:$PORT/calendar.ics`.

## Running behind a WSGI server

For deployments using a WSGI server (e.g. Gunicorn), use the `wsgi.py` module:

```bash
gunicorn wsgi:app
```

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.
