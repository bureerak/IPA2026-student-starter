"""Part 4 student implementation."""

import json

import logging

import os

from concurrent.futures import ThreadPoolExecutor

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from pathlib import Path

from tempfile import TemporaryDirectory

from app.integration import process_request

from app.webex_client import WEBEX_API_BASE, WebexClient

MAX_BODY_BYTES = 1_000_000

REQUEST_TIMEOUT = 10

logger = logging.getLogger(__name__)

class WebexEventHandler:
    def __init__(self, client, bot_person_id, processor=None):
        self.client = client
        self.bot_person_id = bot_person_id
        self.processor = processor if processor is not None else process_request

    def handle_event(self, event):
        if not isinstance(event, dict):
            return None

        if event.get("resource") != "messages":
            return None

        if event.get("event") != "created":
            return None

        data = event.get("data")

        if not isinstance(data, dict):
            return None

        message_id = data.get("id")

        if not message_id:
            return None

        # Skip our own messages before spending a Webex API call.
        if data.get("personId") == self.bot_person_id:
            return None

        message = self.client.get_message(message_id)

        # The event may not carry personId, so check the fetched message too.
        if message.get("personId") == self.bot_person_id:
            return None

        room_id = message.get("roomId")
        mentioned_people = message.get("mentionedPeople") or []
        files = message.get("files") or []

        if len(files) > 1:
            response = {
                "status": "error",
                "result": "multiple_attachments",
            }
        elif not files:
            response = self.processor(
                mentioned_people,
                None,
                self.bot_person_id,
            )
        else:
            content = self.client.download_file(files[0])

            with TemporaryDirectory() as directory:
                path = Path(directory) / "request.yaml"
                path.write_bytes(content)

                response = self.processor(
                    mentioned_people,
                    path,
                    self.bot_person_id,
                )

        self.client.send_message(room_id, json.dumps(response))

        return response

def make_http_handler(submit_event):
    class WebhookHTTPHandler(BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            logger.info("%s - %s", self.address_string(), format % args)

        def _send_json(self, status, payload):
            body = json.dumps(payload).encode()

            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if self.path != "/health":
                self._send_json(404, {"status": "error", "result": "not_found"})
                return

            self._send_json(200, {"status": "ok", "result": "healthy"})

        def do_POST(self):
            if self.path != "/webhook":
                self._send_json(404, {"status": "error", "result": "not_found"})
                return

            invalid = {"status": "error", "result": "invalid_event"}

            try:
                length = int(self.headers.get("Content-Length", 0))
            except (TypeError, ValueError):
                self._send_json(400, invalid)
                return

            if length < 1 or length > MAX_BODY_BYTES:
                self._send_json(400, invalid)
                return

            body = self.rfile.read(length)

            try:
                event = json.loads(body)
            except (ValueError, UnicodeDecodeError):
                self._send_json(400, invalid)
                return

            if not isinstance(event, dict):
                self._send_json(400, invalid)
                return

            submit_event(event)

            self._send_json(200, {"status": "ok", "result": "accepted"})

    return WebhookHTTPHandler

def resolve_bot_person_id(client):
    response = client.session.get(
        f"{WEBEX_API_BASE}/people/me",
        headers=client.headers,
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    return response.json()["id"]

def main():
    logging.basicConfig(level=logging.INFO)

    host = os.getenv("WEBHOOK_HOST", "0.0.0.0")
    port = int(os.getenv("WEBHOOK_PORT", "8000"))

    client = WebexClient()
    bot_person_id = resolve_bot_person_id(client)
    handler = WebexEventHandler(client, bot_person_id)

    # One worker keeps router changes from overlapping.
    executor = ThreadPoolExecutor(max_workers=1)

    def process_in_background(event):
        try:
            handler.handle_event(event)
        except Exception:
            logger.exception("failed to handle Webex event")

    def submit_event(event):
        executor.submit(process_in_background, event)

    server = ThreadingHTTPServer((host, port), make_http_handler(submit_event))

    logger.info("listening on %s:%s as %s", host, port, bot_person_id)

    try:
        server.serve_forever()
    finally:
        server.server_close()
        executor.shutdown(wait=True)

if __name__ == "__main__":
    main()
