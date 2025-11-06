"""
Custom integration to integrate RiverLink SDVoE Matrix with Home Assistant.

For more details about this integration, please refer to
https://github.com/switch180/RiverLink-SDVoE
"""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING

from homeassistant.const import CONF_HOST, CONF_PORT, Platform
from homeassistant.loader import async_get_loaded_integration

from .api import RiverLinkApiClient
from .const import CONF_API_VERSION, DEFAULT_SCAN_INTERVAL, DOMAIN, LOGGER
from .coordinator import RiverLinkDataUpdateCoordinator
from .data import RiverLinkData

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from .data import RiverLinkConfigEntry

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
]


# https://developers.home-assistant.io/docs/config_entries_index/#setting-up-an-entry
async def async_setup_entry(
    hass: HomeAssistant,
    entry: RiverLinkConfigEntry,
) -> bool:
    """Set up this integration using UI."""
    coordinator = RiverLinkDataUpdateCoordinator(
        hass=hass,
        logger=LOGGER,
        name=DOMAIN,
        update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
    )
    
    # Create API client
    client = RiverLinkApiClient(
        host=entry.data[CONF_HOST],
        port=entry.data[CONF_PORT],
        api_version=entry.data[CONF_API_VERSION],
    )
    
    entry.runtime_data = RiverLinkData(
        client=client,
        integration=async_get_loaded_integration(hass, entry.domain),
        coordinator=coordinator,
    )

    # https://developers.home-assistant.io/docs/integration_fetching_data#coordinated-single-api-poll-for-data-for-all-entities
    await coordinator.async_config_entry_first_refresh()

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    return True


async def async_unload_entry(
    hass: HomeAssistant,
    entry: RiverLinkConfigEntry,
) -> bool:
    """Handle removal of an entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_reload_entry(
    hass: HomeAssistant,
    entry: RiverLinkConfigEntry,
) -> None:
    """Reload config entry."""
    await hass.config_entries.async_reload(entry.entry_id)
