"""Constants for the FireboardHA integration."""

DOMAIN = "fireboardha"
MANUFACTURER = "Fireboard Labs"

# API
API_BASE_URL = "https://fireboard.io/api/v1"
API_AUTH_URL = "https://fireboard.io/api/rest-auth/login/"
API_DEVICES_PATH = "/devices.json"
API_USER_AGENT = "FireboardHA Home Assistant Integration"

# Config entry keys
CONF_TOKEN = "token"

# Polling — single /devices.json call includes latest_temps, so 60s is
# well within the 200 calls/hour and 17 calls/5-minute rate limits.
UPDATE_INTERVAL_SECONDS = 60

# Fireboard degreetype field values
DEGREETYPE_CELSIUS = 1
DEGREETYPE_FAHRENHEIT = 2
