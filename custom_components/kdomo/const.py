"""Constants for the independent K-Domo cloud integration."""

DOMAIN = "kdomo"
VERSION = "0.3.0"
BASE_URL = "https://giacomini.kblue.cloud/"
CONF_PLANT_ID = "plant_id"
CONF_PLANT_NAME = "plant_name"
CONF_WRITE_ENABLED = "write_enabled"
CONF_POLL_INTERVAL = "poll_interval"
DEFAULT_POLL_INTERVAL = 60
MIN_POLL_INTERVAL = 60
MAX_POLL_INTERVAL = 600
HEATING_TEMPERATURES = (
    "heatingtempcomfort",
    "heatingtempcomfortplus",
    "heatingtempnight",
    "heatingtempeconomy",
    "tempeconomyplus",
    "tempantifreeze",
)
COOLING_TEMPERATURES = (
    "coolingtempcomfort",
    "coolingtempcomfortplus",
    "coolingtempnight",
    "coolingtempeconomy",
)
PRESET_TEMPERATURES = HEATING_TEMPERATURES + COOLING_TEMPERATURES
PRESET_GROUPS = {
    "10": (HEATING_TEMPERATURES, ("heatinggeoinhome", "heatinggeoouthome", "heatingtype")),
    "11": (COOLING_TEMPERATURES, ("coolinggeoinhome", "coolinggeoouthome", "coolingtype")),
}
PARAMETERS = (
    (
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
    + PRESET_TEMPERATURES
    + tuple(key for _, integers in PRESET_GROUPS.values() for key in integers)
)
