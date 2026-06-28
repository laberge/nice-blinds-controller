# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A Home Assistant **custom integration** (HACS-distributed) that controls Nice blind/shade motors through a Nice HTTP/network controller (IT4WiFi, MyNice, etc.). The integration code lives in `custom_components/blinds_control/`. Everything in the repo root (`blinds`, `send_command.py`, `test_controller.py`, `*.zsh`) is **standalone CLI tooling** that talks to the same controller but is independent of Home Assistant.

There is no build step. The integration is tested with pytest; HACS structure validation runs in CI.

## Commands

- **Set up test env** (one time): `python3 -m venv .venv && .venv/bin/pip install -r requirements-test.txt`. This pulls a full Home Assistant + `pytest-homeassistant-custom-component`.
- **Run tests**: `.venv/bin/pytest` (config in `pyproject.toml`; `asyncio_mode=auto`). Single file: `.venv/bin/pytest tests/test_nice_protocol.py`; single test: `.venv/bin/pytest tests/test_cover.py::test_cover_position_and_states`.
- **Pre-commit** (runs tests + hygiene before every commit): `.venv/bin/pre-commit install` once; then it runs automatically. Manual: `.venv/bin/pre-commit run --all-files`. The `pytest` hook invokes `.venv/bin/pytest`, so the venv must exist.
- **Lint/validate**: CI (`.github/workflows/validate.yml`) runs both HACS validation (`hacs/action@main`) and the pytest job.
- **CLI dev deps**: `pip install -r requirements.txt` (only needed for the standalone scripts; the HA integration relies on HA's bundled `aiohttp`).

## Tests

`tests/` mirrors the three integration layers. `conftest.py` holds the `enable_custom_integrations` fixture and sample controller XML. The protocol layer is tested against mocked HTTP via `aioresponses` (no HA needed); `cover` and `config_flow` use the `hass` fixture. When changing protocol endpoints, command codes, or the `adr`/`ept` ID convention, update `test_nice_protocol.py` in lockstep.
- **Run the CLI**: `./blinds <open|close|stop|status|list|list-groups> ["<device name>"]` and `./blinds <open|close|stop>-group "<group>"`. Configure via env vars `BLINDS_URL`, `BLINDS_USER`, `BLINDS_PASS` (see `BLINDS_CLI_README.md`).
- **Diagnostics**: `./test_controller.py` probes the controller; `./send_command.py` sends raw commands by device ID.

## Releasing

Version is the single source of truth in `custom_components/blinds_control/manifest.json` (`version` field). Bump it, add a `CHANGELOG.md` entry, then commit. HACS picks up GitHub releases/tags. `manifest.json` `requirements` must stay empty — pinning `aiohttp` there breaks HACS installs because HA already provides it (see CHANGELOG 1.9.2).

## Architecture

The integration has three layers:

1. **`nice_protocol.py` — `NiceController`**: the only thing that speaks HTTP to the controller. Owns a single shared `aiohttp.ClientSession` (lazily created via `_ensure_initialized`, closed in `cleanup`). All controller knowledge lives here:
   - CGI endpoints: `cgi/devlst.xml` (device + status list), `cgi/grplst.xml` (groups), `cgi/devcmd.xml?adr=&ept=&cmd=` (single device command), `cgi/grpcmd.xml?req=R&num=&dat=` (group command).
   - Command codes: `stop=02`, `open=03`, `close=04` (group variant pads to `02000000`/`03000000`/`04000000`).
   - **Device ID format is `"adr,ept"` where `adr` is decimal and `ept` is uppercase hex** — the controller XML reports `adr`/`ept` as hex, so discovery converts `adr` hex→decimal but keeps `ept` as hex. Get this conversion wrong and commands silently hit the wrong device.
   - Position: `pos="255"` means unknown/None; otherwise 0–100. Status code `02`=opening, `03`=closing, `04`=open limit, `05`=closed limit.

2. **`cover.py` — entities + polling**: `NiceStatusCoordinator` (a `DataUpdateCoordinator`) polls `get_all_device_status()` every 10s; all entities are `CoordinatorEntity` reading from `coordinator.data` (no per-entity polling). Two entity types:
   - `BlindsCover`: a single motor. Supports open/close/stop/set_position. Position control is **time-based dead reckoning** — it issues open/close, `asyncio.sleep`s for `move_time * (delta/100)`, then stop. There is no closed-loop seeking. `move_time` is a config option (default 30s).
   - `BlindsGroupCover`: maps to a controller's **native hardware group** (`send_group_command`). Groups have no position feedback (`is_*` return False/None) and execute whatever actions are pre-programmed on the controller — the integration cannot introspect group membership.

3. **`config_flow.py` — setup + options**: multi-step config flow (`http_connection` → `select_devices` → `review_groups`). Discovered devices/groups are stored **in the config entry's `data`** (not fetched at runtime), so adding devices/groups on the controller requires the Options flow's **Refresh Devices & Groups** action, which re-discovers and calls `async_reload`.

`__init__.py` registers the controller device and forwards the `cover` platform. `hass.data[DOMAIN][entry_id]` holds `config`, and (after `cover` setup) `controller` + `coordinator`.

## Conventions

- Groups are managed entirely in the Nice controller's web UI (`/grp_list.htm`); this codebase only reads and triggers them. Don't add group-membership editing here.
- The CLI scripts duplicate the protocol logic from `nice_protocol.py` deliberately (they must run without Home Assistant). When changing endpoints/command codes, update both.
