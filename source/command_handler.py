from .logger import logger


class CommandHandler:
    def __init__(self, profile_manager, disk_client):
        self.profiles = profile_manager
        self.disk = disk_client

    def handle_command(self, profile_name: str, message: str):
        """Обрабатывает команды из сообщения."""
        # TODO: Реализовать обработку !лог, !сохрани, !обнови
        pass