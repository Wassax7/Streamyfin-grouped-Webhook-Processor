import os
import time
import threading
import difflib
import logging
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
import requests

# Logging configuration
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# Paramètres d'environnement
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")
SIMILARITY_PREFIX = os.environ.get("SIMILARITY_PREFIX", "Nouvel épisode")
THRESHOLD = int(os.environ.get("THRESHOLD", 5))
BUFFER_TIME = int(os.environ.get("BUFFER_TIME", 20))
HEADER_AUTHORIZATION = os.environ.get("HEADER_AUTHORIZATION")
HEADER_CONTENT_TYPE = os.environ.get("HEADER_CONTENT_TYPE", "application/json")

# Template du body custom récupéré dans l'environnement
CUSTOM_BODY_TEMPLATE = os.environ.get("CUSTOM_BODY_TEMPLATE", "De nouveaux épisodes sont disponible pour {title} (Saison {saison})")
# Custom body template from environment
CUSTOM_BODY_TEMPLATE = os.environ.get("CUSTOM_BODY_TEMPLATE", "De nouveaux épisodes sont disponible pour {title} (Saison {season})")
# Season keyword from environment (e.g. 'Saison' or 'Season')
SEASON_KEYWORD = os.environ.get("SEASON_KEYWORD", "Saison")

# Headers du webhook (n'inclut pas Authorization si non défini)
HEADERS = {}
if HEADER_AUTHORIZATION:
    HEADERS["Authorization"] = HEADER_AUTHORIZATION
if HEADER_CONTENT_TYPE:
    HEADERS["Content-Type"] = HEADER_CONTENT_TYPE

# Buffer + lock
buffer = []
buffer_lock = threading.Lock()
timer = None

def is_similar_title(title):
    """Checks if the title is similar to the defined prefix"""
    similarity = difflib.SequenceMatcher(None, SIMILARITY_PREFIX.lower(), title.lower()).ratio() * 100
    logging.debug(f"Comparing title: '{title}' with prefix '{SIMILARITY_PREFIX}': {similarity:.2f}% similarity")
    return similarity >= THRESHOLD

def send_to_webhook(payload):
    """Sends the filtered data to the webhook"""
    try:
        logging.info(f"Sending filtered payload to webhook ({WEBHOOK_URL}): {payload}")
        response = requests.post(WEBHOOK_URL, headers=HEADERS, json=payload)
        response.raise_for_status()
        logging.info("Webhook sent successfully")
    except Exception as e:
        logging.error(f"Error while sending webhook: {e}")

def buffer_handler():
    """Processes buffer items after timer expiration"""
    global timer
    with buffer_lock:
        logging.info("Time elapsed, starting buffer processing")
        if not buffer:
            logging.warning("Buffer is empty, nothing to send")
            timer = None
            return

        logging.debug(f"Current buffer content ({len(buffer)} items): {buffer}")


        matching_notifs = [item for item in buffer if SIMILARITY_PREFIX in item.get("body", "")]
        non_matching_notifs = [item for item in buffer if SIMILARITY_PREFIX not in item.get("body", "")]

        # Always send non-matching notifications as-is
        for notif in non_matching_notifs:
            send_to_webhook([notif])

        if matching_notifs:
            if len(buffer) > THRESHOLD:
                notif = matching_notifs[0]
                import re
                title = notif.get("title", "")
                username = notif.get("username", "")
                body = notif.get("body", "")
                # Build regex from keyword, allowing any spaces/tabs after
                keyword_escaped = re.escape(SEASON_KEYWORD)
                regex = rf"{keyword_escaped}\s*(\d+)"
                season_match = re.search(regex, body)
                season = season_match.group(1) if season_match else "?"
                custom_body = CUSTOM_BODY_TEMPLATE.format(title=title, season=season)
                custom_notif = {
                    "title": title,
                    "body": custom_body,
                    "username": username
                }
                logging.info(f"Custom notification sent: {custom_notif}")
                send_to_webhook([custom_notif])
            else:
                logging.info(f"Buffer size ({len(buffer)}) is not greater than threshold ({THRESHOLD}), sending all matching notifications.")
                for notif in matching_notifs:
                    send_to_webhook([notif])
        else:
            logging.info(f"No notification with prefix '{SIMILARITY_PREFIX}' found in body")

        buffer.clear()
        timer = None

class WebhookHandler(BaseHTTPRequestHandler):
    def _set_response(self, status=200):
        self.send_response(status)
        self.send_header("Content-type", "application/json")
        self.end_headers()

    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        raw_post_data = self.rfile.read(content_length)

        try:
            post_data = json.loads(raw_post_data)
            logging.info("POST request received")

            # Accepts a list of objects or a single object
            if isinstance(post_data, list):
                items = post_data
            elif isinstance(post_data, dict):
                items = [post_data]
            else:
                logging.warning("Unexpected JSON format (neither object nor list of objects)")
                self._set_response(400)
                return

            logging.debug(f"Received JSON data: {items}")

            with buffer_lock:
                buffer.extend(items)
                logging.info(f"Added to buffer (total: {len(buffer)})")

                global timer
                if timer is not None:
                    timer.cancel()
                    logging.info("Previous timer cancelled for reset.")
                logging.info(f"(Re)starting timer ({BUFFER_TIME}s)")
                timer = threading.Timer(BUFFER_TIME, buffer_handler)
                timer.start()

            self._set_response()

        except json.JSONDecodeError:
            logging.error("JSON parsing failed")
            self._set_response(400)

def run_server(server_class=HTTPServer, handler_class=WebhookHandler, port=8000):
    server_address = ("", port)
    httpd = server_class(server_address, handler_class)
    logging.info(f"Server listening on port {port}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logging.info("Server shutdown requested")
    finally:
        httpd.server_close()
        logging.info("Server stopped cleanly")

if __name__ == "__main__":
    run_server()