import json
import os
import sys
import time
from io import BytesIO

import requests
from PIL import Image
from RGBMatrixEmulator import RGBMatrix, RGBMatrixOptions

from spotify import get_currently_playing, refresh_access_token

config = {
    "rows": 64,
    "columns": 64,
    "chain_length": 1,
    "parallel": 1,
    "hardware_mapping": "adafruit-hat-pwm",
    "gpio_slowdown": 2,
    "brightness": 70,
    "default_image": "assets/default.png",
    "power": "on",
    "refresh_rate": 60,
}


def get_album_art():
    with open("tokens.json", "r") as f:
        tokens = json.load(f)

    playing = get_currently_playing(tokens["access_token"])

    if playing.get("error") == "Token expired":
        token_data = refresh_access_token(tokens["refresh_token"])
        tokens.update(token_data)
        with open("tokens.json", "w") as f:
            json.dump(tokens, f)
        playing = get_currently_playing(tokens["access_token"])

    album_art_url = playing["item"]["album"]["images"][0]["url"]  # pyright: ignore[reportArgumentType]
    print(album_art_url)

    return album_art_url


def main():

    options = RGBMatrixOptions()
    options.rows = int(config["rows"])
    options.cols = int(config["columns"])
    options.chain_length = int(config["chain_length"])
    options.parallel = int(config["parallel"])
    options.hardware_mapping = config["hardware_mapping"]
    options.gpio_slowdown = int(config["gpio_slowdown"])  # pyright: ignore[reportAttributeAccessIssue]
    options.brightness = int(config["brightness"])
    options.limit_refresh_rate_hz = int(config["refresh_rate"])  # pyright: ignore[reportAttributeAccessIssue]

    default_image = os.path.join(os.path.dirname(__file__), config["default_image"])
    matrix = RGBMatrix(options=options)
    canvas = matrix.CreateFrameCanvas()

    previous_album_url = ""
    current_album_url = ""

    try:
        while True:
            try:
                current_album_url = get_album_art()

                if previous_album_url != current_album_url:
                    response = requests.get(current_album_url)
                    response.raise_for_status()
                    image = Image.open(BytesIO(response.content))
                    previous_album_url = current_album_url
            except Exception:
                image = Image.open(default_image)
            finally:
                image.thumbnail((matrix.width, matrix.height), Image.Resampling.LANCZOS)

                canvas.SetImage(image.convert("RGB"))
                canvas = matrix.SwapOnVSync(canvas)

                time.sleep(1)

    except KeyboardInterrupt:
        sys.exit(0)


if __name__ == "__main__":
    main()
