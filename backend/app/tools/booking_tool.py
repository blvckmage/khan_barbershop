from app.services.alteegio_service import alteegio_service

class BookingTool:
    """Инструмент для создания записи."""
    @staticmethod
    async def create_booking(staff_id: str, service_id: str, date: str, time: str, client_phone: str, client_name: str):
        return await alteegio_service.create_appointment(staff_id, service_id, date, time, client_phone, client_name)
