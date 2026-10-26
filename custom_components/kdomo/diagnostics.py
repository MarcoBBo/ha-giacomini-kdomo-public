"""Allowlisted diagnostics: no account, plant names, serials, token or raw API data."""

from .const import CONF_POLL_INTERVAL, CONF_WRITE_ENABLED, DEFAULT_POLL_INTERVAL


async def async_get_config_entry_diagnostics(hass, entry) -> dict:
    coordinator = entry.runtime_data
    return {
        "integration_version": "0.1.0",
        "options": {
            CONF_WRITE_ENABLED: entry.options.get(CONF_WRITE_ENABLED, False),
            CONF_POLL_INTERVAL: entry.options.get(CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL),
        },
        "last_update_success": coordinator.last_update_success,
        "devices": [
            {
                "online": state.online,
                "read_error": state.error,
                "scale": state.scale,
                "mode": state.integer("mode"),
                "status": state.integer("status"),
                "program": state.integer("program"),
            }
            for state in (coordinator.data or {}).values()
        ],
    }
