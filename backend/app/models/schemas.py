from pydantic import BaseModel
from typing import Optional, List, Any
from datetime import datetime


# Request models
class ManyChatRequest(BaseModel):
    """Request from ManyChat webhook"""
    user_input: str
    user_phone: str
    stoplist: Optional[str] = None


class ChatRequest(BaseModel):
    """Generic chat request"""
    message: str
    session_id: str
    user_phone: Optional[str] = None


# Response models
class ChatResponse(BaseModel):
    """Response to ManyChat"""
    output: str


# Alteegio API models
class AlteegioService(BaseModel):
    """Service in appointment"""
    id: str
    amount: int = 1


class AlteegioClient(BaseModel):
    """Client information"""
    phone: str
    name: str


class CreateAppointmentRequest(BaseModel):
    """Request to create appointment in Alteegio"""
    staff_id: str
    services: List[AlteegioService]
    client: AlteegioClient
    datetime: str  # ISO format: 2025-12-04T10:00:00
    seance_length: str  # Duration in seconds
    comment: str = "ЗАПИСЬ СДЕЛАНА ЧЕРЕЗ БОТА!!!"


class CreateAppointmentResponse(BaseModel):
    """Response from Alteegio appointment creation"""
    success: bool
    id: Optional[int] = None
    error: Optional[str] = None


class StaffMember(BaseModel):
    """Staff member from Alteegio"""
    id: int
    name: str
    specialization: Optional[str] = None
    bookable: bool = True


class AvailableTime(BaseModel):
    """Available time slot"""
    time: str
    available: bool


class ServiceInfo(BaseModel):
    """Service information from Google Sheets"""
    service_id: str
    service_name: str
    staff_id: str
    staff_name: str
    seance_length: int  # in seconds
    price: int


class StaffInfo(BaseModel):
    """Staff information from Google Sheets"""
    staff_id: str
    staff_name: str