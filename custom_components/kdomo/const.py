"""Constants for the independent K-Domo cloud integration."""

DOMAIN = "kdomo"
BASE_URL = "https://giacomini.kblue.cloud/"
CONF_PLANT_ID = "plant_id"
CONF_PLANT_NAME = "plant_name"
CONF_WRITE_ENABLED = "write_enabled"
CONF_POLL_INTERVAL = "poll_interval"
DEFAULT_POLL_INTERVAL = 60
MIN_POLL_INTERVAL = 60
MAX_POLL_INTERVAL = 600
PARAMETERS = (
    "name",
    "temperature",
    "humidity",
    "currentsetpoint",
    "mode",
    "program",
    "status",
    "scale",
    "fancoil",
    "prog0",
    "prog1",
    "prog2",
    "prog3",
    "prog4",
    "prog5",
)
