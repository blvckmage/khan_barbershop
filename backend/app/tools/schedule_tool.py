from app.services.alteegio_service import alteegio_service

class ScheduleTool:
    """Инструмент для получения расписания мастеров."""
    @staticmethod
    async def get_schedule(staff_id: str, date: str):
        return await alteegio_service.get_staff_schedule(staff_id, date)
