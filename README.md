# FireboardHA

A custom Home Assistant integration for the [Fireboard Digital Thermometer](https://fireboard.io). Exposes every temperature probe as an individual sensor entity, named after the probe labels you set in the Fireboard app, and grouped by device — ready for temperature trend graphs out of the box.

---

## Features

- **Per-probe sensors** — each active channel gets its own HA sensor entity
- **Probe labels** — sensors are named after the labels you set in the Fireboard app (e.g. "Grate", "Brisket"); renames are picked up automatically on the next poll
- **Multi-device support** — multiple Fireboard devices each appear as a separate device in HA
- **Temperature history graphs** — works with the built-in history-graph card; HA stores short- and long-term statistics automatically
- **Dynamic discovery** — new probes are added as entities the moment they report a reading; no restart required
- **Always Fahrenheit** — all sensors report in °F regardless of device configuration
- **UI-based setup** — no YAML required; configure via Settings → Devices & Services
- **Cloud polling** — polls the Fireboard API every 60 seconds, well within the 200 calls/hour rate limit

---

## Requirements

- Home Assistant 2023.1 or later
- A [Fireboard account](https://fireboard.io) with at least one device

---

## Installation

### HACS (recommended)

1. Open HACS in Home Assistant
2. Go to **Integrations** → **Custom repositories**
3. Add `https://github.com/jasonmull/FireboardHA` with category **Integration**
4. Search for "FireboardHA" and install
5. Restart Home Assistant

### Manual

1. Download or clone this repository
2. Copy the `custom_components/fireboardha/` directory into your Home Assistant `custom_components/` directory
3. Restart Home Assistant

---

## Setup

1. Go to **Settings → Devices & Services → Add Integration**
2. Search for **FireboardHA**
3. Enter your Fireboard account **username** and **password**
4. Click **Submit** — your devices and probes will appear automatically

---

## Entities

Each probe channel that has reported at least one reading becomes a sensor entity. Entities are named using the pattern:

```
{Device Title} {Probe Label}
```

For example, a device named "Big Green Egg" with probes labelled "Grate" and "Brisket" produces:

| Entity ID | Name |
|---|---|
| `sensor.big_green_egg_grate` | Big Green Egg Grate |
| `sensor.big_green_egg_brisket` | Big Green Egg Brisket |

If a probe has no label set in the Fireboard app, it falls back to **Probe 1**, **Probe 2**, etc.

### Availability

A probe sensor shows as **unavailable** when:
- The probe is unplugged or out of range
- The last reading is older than 60 seconds (Fireboard API behavior)
- The Fireboard cloud API is unreachable

---

## Temperature History Graph

Add this card to any Lovelace dashboard to visualize temperature trends:

```yaml
type: history-graph
title: Fireboard Temperatures
entities:
  - sensor.big_green_egg_grate
  - sensor.big_green_egg_brisket
hours_to_show: 8
```

The history-graph card works automatically because all sensors use `state_class: measurement` and `device_class: temperature`. Home Assistant stores both short-term (5-minute) and long-term (hourly) statistics for every probe.

---

## Technical Details

| Item | Value |
|---|---|
| Domain | `fireboardha` |
| IoT class | `cloud_polling` |
| Poll interval | 60 seconds |
| API base URL | `https://fireboard.io/api/v1` |
| Temperature unit | Fahrenheit (°F) |

---

## License

MIT
