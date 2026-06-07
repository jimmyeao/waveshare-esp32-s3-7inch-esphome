# Wall-panel album-art resizer
# Place at: /config/pyscript/wallpanel_art.py
#
# Why this exists: media_player `entity_picture` art can be huge (2000x3000+).
# An ESP32-S3 decodes the *full* image before it can resize, which blocks the
# main loop for tens of seconds and hangs the device. So we resize on the HA
# side and serve a small static JPEG the panel can decode in milliseconds.
#
# Requires the "pyscript" integration (install via HACS, then add it through
# Settings -> Devices & Services -> Add Integration -> Pyscript, and enable
# "Allow All Imports" in its options).

import requests
from PIL import Image
from io import BytesIO

BASE = "http://127.0.0.1:8123"   # HA fetching its own proxy URL (local, no TLS)
OUT = "/config/www"               # served at http://<ha>:8123/local/...


@service
def wp_resize_art(entity_id=None, name=None):
    """Download a media_player's current artwork, shrink it, save as /config/www/wp_<name>.jpg."""
    attrs = state.getattr(entity_id) or {}
    pic = attrs.get("entity_picture")
    if not pic:
        return
    url = BASE + pic if pic.startswith("/") else pic
    r = task.executor(requests.get, url, timeout=10)
    if r.status_code != 200:
        log.warning(f"wp_resize_art: {entity_id} art fetch returned {r.status_code}")
        return
    img = task.executor(Image.open, BytesIO(r.content)).convert("RGB")
    img.thumbnail((400, 400))     # long edge <= 400px; panels downscale crisply
    task.executor(img.save, f"{OUT}/wp_{name}.jpg", "JPEG", quality=85)
