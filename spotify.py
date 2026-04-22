import base64
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from os import getenv
from urllib.parse import parse_qs, urlencode, urlparse

import requests
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = getenv("SPOTIFY_CLIENT_ID")
CLIENT_SECRET = getenv("SPOTIFY_CLIENT_SECRET")
REDIRECT_URI = getenv("REDIRECT_URI")
SCOPE = "user-read-currently-playing user-read-playback-state"

AUTH_URL = "https://accounts.spotify.com/authorize"
TOKEN_URL = "https://accounts.spotify.com/api/token"
NOW_PLAYING_URL = "https://api.spotify.com/v1/me/player/currently-playing"

TOKENS = {}


def get_basic_auth_header():
    creds = f"{CLIENT_ID}:{CLIENT_SECRET}".encode()
    return {
        "Authorization": "Basic " + base64.b64encode(creds).decode(),
        "Content-Type": "application/x-www-form-urlencoded",
    }


def exchange_code_for_token(code):
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
    }

    r = requests.post(TOKEN_URL, data=data, headers=get_basic_auth_header())
    r.raise_for_status()
    return r.json()


def refresh_access_token(refresh_token):
    data = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
    }

    r = requests.post(TOKEN_URL, data=data, headers=get_basic_auth_header())
    r.raise_for_status()
    return r.json()


def get_currently_playing(access_token: str):
    headers = {"Authorization": f"Bearer {access_token}"}
    r = requests.get(NOW_PLAYING_URL, headers=headers)

    if r.status_code == 204:
        return {"status": "No track currently playing"}
    if r.status_code == 401:
        return {"error": "Token expired"}

    return r.json()


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path == "/":
            params = {
                "client_id": CLIENT_ID,
                "response_type": "code",
                "redirect_uri": REDIRECT_URI,
                "scope": SCOPE,
            }
            url = AUTH_URL + "?" + urlencode(params)

            self.send_response(302)
            self.send_header("Location", url)
            self.end_headers()

        elif parsed.path == "/callback":
            query = parse_qs(parsed.query)
            code = query.get("code", [None])[0]

            if not code:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b"Missing code")
                return

            token_data = exchange_code_for_token(code)
            TOKENS.update(token_data)

            with open("tokens.json", "w") as f:
                json.dump(TOKENS, f)

            self.send_response(204)
            self.send_header("Content-Type", "application/json")
            self.end_headers()

        elif parsed.path == "/refresh":
            if "refresh_token" not in TOKENS:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b"No refresh token available")
                return

            token_data = refresh_access_token(TOKENS["refresh_token"])
            TOKENS.update(token_data)

            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"Token refreshed")

        else:
            self.send_response(404)
            self.end_headers()


def run():
    server = HTTPServer(("127.0.0.1", 8888), Handler)
    print("Server running at http://127.0.0.1:8888")
    server.serve_forever()


if __name__ == "__main__":
    run()
