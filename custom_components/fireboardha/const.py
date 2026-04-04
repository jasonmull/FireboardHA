"""Constants for the FireboardHA integration."""

DOMAIN = "fireboardha"
MANUFACTURER = "Fireboard Labs"

# API
API_BASE_URL = "https://fireboard.io/api/v1"
API_AUTH_URL = "https://fireboard.io/api/rest-auth/login/"
API_DEVICES_PATH = "/devices.json"
API_TEMPS_PATH = "/devices/{uuid}/temps.json"
API_USER_AGENT = "FireboardHA Home Assistant Integration"

# Config entry keys
CONF_TOKEN = "token"

# Polling
UPDATE_INTERVAL_SECONDS = 60

# Fireboard degreetype field values
DEGREETYPE_CELSIUS = 1
DEGREETYPE_FAHRENHEIT = 2
