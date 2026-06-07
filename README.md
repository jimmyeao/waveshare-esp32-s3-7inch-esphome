# ESPHome Home Assistant Wall Panel — Waveshare ESP32-S3-Touch-LCD-7

A wall-mounted touchscreen for Home Assistant built on the **Waveshare ESP32-S3-Touch-LCD-7** (800×480 RGB capacitive display), running entirely in **ESPHome + LVGL** — no Home Assistant dashboard rendering, no browser. The panel talks to HA over the native API.

**Five tabs:**

- **Lights** — 10 colour-aware tiles. A tile that's on shows the light's actual RGB colour; on-but-no-colour falls back to an accent; off is dark. Tap to toggle.
- **Music** — now-playing title/artist/state, transport (prev / play-pause / next), volume, and album art for a Music Assistant player.
- **Spotify** — same layout, pointed at a SpotifyPlus player.
- **Plex** — now-playing + large album art for whichever Plex client is currently playing (read-only; see note).
- **Climate** — current temp, target with −/+, action state, and a Boost button (Hive).

A persistent bottom tab bar switches pages; the active tab is highlighted.

> This is a working personal build. Entity IDs, the HA URL, and the Spotify/Plex/climate specifics are **mine** — you must replace them with your own (see [Customising](#customising)).

---

## Hardware

- **Waveshare ESP32-S3-Touch-LCD-7**, Rev 1.2 (ESP32-S3-WROOM-1, 8 MB octal PSRAM, 800×480 RGB panel, GT911 capacitive touch). The model string in the boot log is `ESP32-S3-TOUCH-LCD-7-800X480`.
- USB-C cable (data, not charge-only) for the first flash.
- A 5 V supply that can actually drive the panel + backlight. A weak laptop port can brown out during display init.

---

## Prerequisites

- **ESPHome 2025.8.0 or newer** (the board package requires it).
- **Home Assistant** with the ESPHome integration.
- For album art: the **pyscript** integration (HACS) and a `template:` block — see [Album art](#album-art-the-hard-part).

---

## Repo layout

```
wall-panel.yaml                         # the ESPHome config (flash this)
secrets.example.yaml                    # ESPHome secrets template
homeassistant/
  pyscript/wallpanel_art.py             # server-side art resizer
  automations.example.yaml              # triggers the resizer on art changes
  templates.example.yaml                # "active Plex client" sensor
```

The board's low-level setup (RGB pin map, GT911 touch, PSRAM, backlight, anti-burn) is **not** in `wall-panel.yaml` — it comes from a community package, pulled automatically:

```yaml
packages:
  waveshare:
    url: https://github.com/inytar/waveshare-esp32-s3-touch-lcd-7-esphome
    files: [waveshare-esp32-s3-touch-lcd-7.yaml]
    ref: main
```

---

## Install

### 1. ESPHome config

1. Put your Wi-Fi / API / OTA values in `secrets.yaml` (see `secrets.example.yaml`).
2. In `wall-panel.yaml`, set the substitutions near the top:
   - `ha_base_url` — your HA URL. **Use the local one** (e.g. `http://192.168.0.237:8123`), not an external/HTTPS URL: art is fetched repeatedly and you want it on-LAN with no TLS.
   - `spotify_player` — your Spotify (or SpotifyPlus) `media_player` entity.
3. Replace the light, media, and climate entity IDs with your own (see [Customising](#customising)).

### 2. First flash (do this wired)

Flash over **USB serial**, not wirelessly — there's no firmware on the board yet to receive OTA. If the chip won't be detected, hold **BOOT**, tap **RESET**, release BOOT to force the ROM bootloader, and try the other USB-C port (the board has two; one is native USB, one is the UART bridge).

> The config ships with `logger: hardware_uart: UART0` so logs appear on the UART-bridge port alongside the ROM bootloader output — handy while debugging. Once stable, change it back to plain `logger:`.

### 3. Add the device to Home Assistant

Settings → Devices & Services → ESPHome → add `wall-panel`. Then **enable "Allow the device to perform Home Assistant actions"** in the device's *Configure* dialog — **without this, taps do nothing** (the device is blocked from calling services by default).

### 4. Album art (see below)

---

## Album art (the hard part)

ESPHome's `online_image` decodes the **full** image before resizing, and media art is often enormous (a 2000×3000 cover took **34 seconds** to decode on-device and hung the panel). It also only decodes **one format** (we use JPEG) and chokes on progressive JPEGs. The fix is to **resize on the HA side** and serve a small static JPEG.

**Setup:**

1. Install **pyscript** via HACS ("Pyscript Python scripting", from the repo root `custom-components/pyscript`), then **restart HA**.
2. Add the integration: **Settings → Devices & Services → Add Integration → Pyscript**, and enable **Allow All Imports** in its options (required, or `import requests`/PIL is blocked). This is done through the UI, not `configuration.yaml`. Confirm `pyscript.reload` appears in Developer Tools → Actions.
3. Copy `homeassistant/pyscript/wallpanel_art.py` to `/config/pyscript/`. Reload pyscript. Confirm `pyscript.wp_resize_art` now exists as an action.
4. Make sure `/config/www/` exists (create it if not).
5. Add the automations from `automations.example.yaml` (edit entity IDs).
6. For the Plex tab, add the sensor from `templates.example.yaml`.
7. Play something on each source so `wp_music.jpg` / `wp_spotify.jpg` / `wp_plex.jpg` get written to `/config/www/`. Verify in a browser: `http://<ha>:8123/local/wp_music.jpg`.

**How it flows:** a player's art changes → the automation calls `wp_resize_art` → pyscript downloads, shrinks (≤400 px), and writes `/config/www/wp_<source>.jpg` → the panel re-fetches that static `/local/` URL on tab load and ~3 s after a track change. Each tab has its own image buffer, so art never bleeds between tabs.

> **Known limitation — the 3 s timing.** The panel re-fetches a fixed 3 s after a track-title change, assuming HA has finished resizing by then. If you ever see art a track behind, raise that delay (in each `*_title` sensor's `on_value`) or wire an explicit "art ready" signal from pyscript.

---

## Customising

**Lights** — each tile is one `binary_sensor` (drives colour) + one `light_*_rgb` text sensor (drives the colour value) + one tile button (toggles). Replace the four light entity references per tile with your own, keep the IDs (`tile_N`, `light_N_state`, `light_N_rgb`) in sync.

**Theme** — colours are literal hex in the file (search/replace): background `0x0B0E14`, surface `0x1A1F2B`, accent `0xFFB454`, text `0xE6E9EF`, dim `0x7A8290`.

**Tile labels / count** — labels live in each `tile_N_lbl`. The grid is 5×2; changing the count means adjusting the grid maths and the `sync_tiles` script.

**Climate Boost** — wired to `climate.set_preset_mode` / `preset_mode: boost`, which is the standard. If your integration exposes boost differently (some use a custom service), change that button's action.

---

## Why the config looks the way it does (hard-won notes)

These are the things that cost real debugging time:

- **PSRAM at 80 MHz, not the package default 120 MHz.** 120 MHz octal PSRAM is batch-sensitive on these modules and caused an early boot loop (`rst:0xc RTC_SW_CPU_RST`, ~1 s) before the logger even came up. `psram: { mode: octal, speed: 80MHz }` fixed it.
- **`CONFIG_LCD_RGB_RESTART_IN_VSYNC` + `full_refresh`.** RGB panels tear/jump on partial redraws. `full_refresh: true` plus the IDF vsync-restart flag (and the PSRAM fetch/rodata flags) make redraws clean.
- **Never put `${substitutions}` inside an inline YAML flow map** (`{ ... }`). The `${}` braces collide with the flow-map braces and YAML fails to parse. Colours are therefore literal hex inline; substitutions are only used in block style.
- **`homeassistant.service` / `component.update`.** Tile/transport actions use `homeassistant.service`; `online_image` is refreshed with `component.update` (there is no `online_image.update` action).
- **State sync on connect.** `sync_tiles` runs on every light change *and* ~3 s after the API connects, so tiles show correct colour at boot rather than defaulting off.

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Boot loop, ~1 s, only ROM banner, no ESPHome log | PSRAM at 120 MHz | Force `psram: speed: 80MHz` |
| "Configuration does not match the platform… UNKNOWN" on flash | Chip not detected | Hold BOOT, tap RESET; try the other USB-C port; use a data cable |
| Display works but no touch (raw touch test logs nothing) | GT911 not seen | Check `i2c` boot scan for `0x5D`; reseat the touch FPC ribbon |
| Tap logs `tapped` but light doesn't change | HA actions disabled | Enable "Allow the device to perform Home Assistant actions" |
| Tiles don't reflect state | Wrong entity IDs / both halves not updated | Each light appears in a `binary_sensor` **and** the tile `on_click` — both must match |
| Panel renders but you see only ROM resets on serial | Watching the wrong port | ESPHome logs default to native USB; set `logger: hardware_uart: UART0` to see them on the bridge port |
| Album art hangs the device | Decoding a full-size image | Resize on the HA side (pyscript); never let the ESP decode multi-MP images |
| Art 404s | `/config/www/wp_*.jpg` not generated | Check pyscript is installed + `allow_all_imports`, `/config/www` exists, and the player has art |
| Art looks soft after enlarging | Source file smaller than the widget | Raise `img.thumbnail((N, N))` in the pyscript |
| Plex transport buttons do nothing | Plex web client doesn't support remote control | Expected; controls are read-only for that client. Point Plex at a TV/mobile client to control it |

---

## Credits

- Board package: [inytar/waveshare-esp32-s3-touch-lcd-7-esphome](https://github.com/inytar/waveshare-esp32-s3-touch-lcd-7-esphome)
- Built with [ESPHome](https://esphome.io) and [LVGL](https://lvgl.io).

## License

MIT — do what you like, no warranty.
