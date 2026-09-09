import asyncio
from . import lv2


class Lv2Core:
    def __init__(self):
        self.lv2_manager: lv2.Lv2Manager = None
        self.lv2_plugin_available_list = None

        self.selected_plugins: dict = None

    @property
    def is_initialized(self):
        return (
            self.lv2_manager is not None and self.lv2_plugin_available_list is not None
        )

    # Only initialize if needed. Unnecessary initialization takes 3–7 seconds.
    async def init(self):
        if self.lv2_manager is not None or self.lv2_plugin_available_list is not None:
            raise ValueError("Lv2Core already initialized.")

        self.lv2_manager = await asyncio.to_thread(lv2.Lv2Manager)
        self.lv2_plugin_available_list = await asyncio.to_thread(
            self.lv2_manager.get_available_plugins
        )

    async def get_available_plugins(self, callback=None):
        if self.lv2_plugin_available_list is None:
            await self.init()

        if callback is not None:
            callback(self.lv2_plugin_available_list)

        return self.lv2_plugin_available_list

    def get_available_plugins_for_callback(self, callback):
        if self.lv2_plugin_available_list is None:
            asyncio.create_task(self.get_available_plugins(callback))
        else:
            callback(self.lv2_plugin_available_list)
