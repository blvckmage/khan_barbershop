from app.services.sheets_service import sheets_service

class AllStaffTool:
    """Инструмент для получения списка всех мастеров."""
    @staticmethod
    async def get_all_staff():
        return sheets_service.get_all_staff()
