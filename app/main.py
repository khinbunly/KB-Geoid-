"""Application entry point and Telegram Bot runner with HTTP healthcheck server for Cloud hosting."""

import asyncio
from http.server import BaseHTTPRequestHandler, HTTPServer
import os
from pathlib import Path
import sys
import threading

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from telegram import Update
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    filters,
)
from app.config import settings
from app.handlers.error import global_error_handler
from app.handlers.file import document_handler
from app.handlers.location import location_handler
from app.handlers.single import single_point_handler
from app.handlers.start import (
    about_handler,
    help_handler,
    utm_guide_handler,
    menu_callback_handler,
    start_handler,
)
from app.utils.logger import logger


class HealthCheckHandler(BaseHTTPRequestHandler):
    """Simple HTTP server to satisfy Cloud (Hugging Face / Render / Koyeb) healthchecks."""

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.end_headers()
        html_page = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>KB-Geoid Telegram Bot</title>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0f172a; color: #f8fafc; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; }
                .card { background: #1e293b; padding: 40px; border-radius: 16px; box-shadow: 0 10px 25px rgba(0,0,0,0.5); text-align: center; max-width: 450px; border: 1px solid #334155; }
                .badge { background: #22c55e; color: #000; padding: 6px 14px; border-radius: 20px; font-weight: bold; font-size: 14px; display: inline-block; margin-bottom: 20px; }
                h1 { margin: 0 0 10px; font-size: 24px; color: #38bdf8; }
                p { color: #94a3b8; font-size: 15px; line-height: 1.5; margin: 10px 0; }
                .btn { display: inline-block; background: #0ea5e9; color: white; text-decoration: none; padding: 12px 24px; border-radius: 8px; font-weight: 600; margin-top: 20px; transition: background 0.2s; }
                .btn:hover { background: #0284c7; }
            </style>
        </head>
        <body>
            <div class="card">
                <div class="badge">🟢 LIVE 24/7</div>
                <h1>🌐 KB-Geoid Bot</h1>
                <p>EGM2008 Geoid Undulation & MSL ↔ Ellipsoidal Height Engine is running in the cloud.</p>
                <a class="btn" href="https://t.me/KB_Geoid_bot" target="_blank">Open Telegram Bot (@KB_Geoid_bot)</a>
            </div>
        </body>
        </html>
        """
        self.wfile.write(html_page.encode("utf-8"))

    def log_message(self, format, *args):
        # Silence default access logging to keep console clean
        return


def start_health_server(port: int = 7860) -> None:
    """Start background HTTP health server."""
    try:
        server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        logger.info(f"Health check HTTP web server listening on http://0.0.0.0:{port}")
    except Exception as e:
        logger.warning(f"Could not start HTTP health server on port {port}: {e}")


def build_application() -> Application:
    """Build and configure the Telegram application with all handlers."""
    token = settings.TELEGRAM_BOT_TOKEN

    if not token or token == "YOUR_TELEGRAM_BOT_TOKEN_HERE":
        logger.error(
            "TELEGRAM_BOT_TOKEN is not set or contains default placeholder.\n"
            "Please configure your bot token in .env or environment variables.\n"
            "Example: TELEGRAM_BOT_TOKEN=1234567890:ABCdefGhIJKlmNoPQRsTUVwxyZ"
        )
        raise ValueError("Invalid TELEGRAM_BOT_TOKEN. Please set it in .env.")

    # Initialize Telegram Application
    application = ApplicationBuilder().token(token).build()

    # Command Handlers
    application.add_handler(CommandHandler(["start", "menu"], start_handler))
    application.add_handler(CommandHandler(["help", "guide"], help_handler))
    application.add_handler(CommandHandler(["utm", "utm_guide"], utm_guide_handler))
    application.add_handler(CommandHandler(["about", "info"], about_handler))
    application.add_handler(CommandHandler(["mode", "settings"], start_handler))

    # Callback Query Handlers (Buttons)
    application.add_handler(CallbackQueryHandler(menu_callback_handler))

    # Message Handlers
    application.add_handler(MessageHandler(filters.LOCATION, location_handler))
    application.add_handler(MessageHandler(filters.Document.ALL, document_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, single_point_handler))

    # Global Error Handler
    application.add_error_handler(global_error_handler)

    return application



def start_self_ping(url: str = "https://kb-geoid-bot-free.onrender.com", interval_sec: int = 600) -> None:
    """Background thread to keep Render free tier awake 24/7."""
    import time, requests

    def _ping_loop():
        time.sleep(20)
        while True:
            try:
                requests.get(url, timeout=10)
                logger.info(f"24/7 Self-ping to {url} sent.")
            except Exception as e:
                logger.debug(f"Self-ping error: {e}")
            time.sleep(interval_sec)

    t = threading.Thread(target=_ping_loop, daemon=True)
    t.start()


def main() -> None:
    """Main runner function."""
    logger.info("Starting KB-Geoid Telegram Bot...")
    logger.info(f"Environment: {settings.APP_ENV} | Backend: {settings.GEOID_BACKEND}")

    # Start HTTP health server for cloud platforms (Hugging Face Spaces, Render, Koyeb)
    port = int(os.environ.get("PORT", "7860"))
    start_self_ping()
    start_health_server(port)

    try:
        app = build_application()
        logger.info("Bot application initialized successfully. Starting polling...")
        app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.critical(f"Fatal error while running bot: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
