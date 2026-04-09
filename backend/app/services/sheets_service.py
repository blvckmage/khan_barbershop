import gspread
import logging
import time
from typing import List, Dict, Any, Optional
from google.oauth2.service_account import Credentials
from app.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

# TTL для кэша в секундах (5 минут)
CACHE_TTL = 300


class GoogleSheetsService:
    """Service for interacting with Google Sheets with caching"""
    
    def __init__(self):
        self.credentials = Credentials.from_service_account_file(
            settings.google_credentials_path,
            scopes=['https://www.googleapis.com/auth/spreadsheets.readonly']
        )
        self.client = gspread.authorize(self.credentials)
        self._staff_sheet = None
        self._services_sheet = None
        
        # Кэш данных
        self._staff_cache: Dict[str, Any] = {"data": None, "timestamp": 0}
        self._services_cache: Dict[str, Any] = {"data": None, "timestamp": 0}
        
        logger.info("📊 GoogleSheetsService initialized with caching")
    
    @property
    def staff_sheet(self):
        """Lazy load staff spreadsheet"""
        if self._staff_sheet is None:
            self._staff_sheet = self.client.open_by_key(settings.staff_spreadsheet_id)
        return self._staff_sheet
    
    @property
    def services_sheet(self):
        """Lazy load services spreadsheet"""
        if self._services_sheet is None:
            self._services_sheet = self.client.open_by_key(settings.services_spreadsheet_id)
        return self._services_sheet
    
    def _is_cache_valid(self, cache: Dict) -> bool:
        """Check if cache is still valid"""
        return cache["data"] is not None and (time.time() - cache["timestamp"]) < CACHE_TTL
    
    def _get_cached_staff(self) -> List[Dict[str, Any]]:
        """Get staff data from cache or fetch from Google Sheets"""
        if self._is_cache_valid(self._staff_cache):
            logger.info("📋 Using cached staff data")
            return self._staff_cache["data"]
        
        logger.info("📋 Fetching staff data from Google Sheets")
        worksheet = self.staff_sheet.worksheet("staff")
        records = worksheet.get_all_records()
        self._staff_cache = {"data": records, "timestamp": time.time()}
        logger.info(f"   Cached {len(records)} staff members")
        return records
    
    def _get_cached_services(self) -> List[Dict[str, Any]]:
        """Get services data from cache or fetch from Google Sheets"""
        if self._is_cache_valid(self._services_cache):
            logger.info("📋 Using cached services data")
            return self._services_cache["data"]
        
        logger.info("📋 Fetching services data from Google Sheets")
        worksheet = self.services_sheet.get_worksheet(0)
        records = worksheet.get_all_records()
        
        # Логируем первую запись чтобы увидеть реальные названия колонок
        if records:
            logger.info(f"   Raw columns: {list(records[0].keys())}")
            logger.info(f"   First record: {records[0]}")
        
        self._services_cache = {"data": records, "timestamp": time.time()}
        logger.info(f"   Cached {len(records)} services")
        return records
    
    def invalidate_cache(self):
        """Invalidate all caches"""
        self._staff_cache = {"data": None, "timestamp": 0}
        self._services_cache = {"data": None, "timestamp": 0}
        logger.info("🗑️ Cache invalidated")
    
    def get_all_staff(self) -> List[Dict[str, Any]]:
        """
        Get all staff members with their IDs.
        Returns only essential fields: staff_id, name
        """
        logger.info("📋 get_all_staff called")
        records = self._get_cached_staff()
        
        # Возвращаем только нужные поля (экономия токенов)
        result = []
        for staff in records:
            result.append({
                "staff_id": staff.get("staff_id") or staff.get("Staff ID") or staff.get("id"),
                "name": staff.get("name") or staff.get("Name") or staff.get("staff_name")
            })
        
        logger.info(f"   Returning {len(result)} staff members")
        return result
    
    def get_all_services(self) -> List[Dict[str, Any]]:
        """
        Get all services - DEPRECATED, use get_services_by_staff_name instead.
        Returns only service names and staff names for overview.
        """
        logger.info("📋 get_all_services called (limited output)")
        records = self._get_cached_services()
        
        # Возвращаем только имена услуг и мастеров (без ID и цен)
        seen_services = set()
        result = []
        for service in records:
            service_name = service.get("Service Name") or service.get("service_name")
            staff_name = service.get("Staff Name") or service.get("staff_name")
            key = f"{service_name}_{staff_name}"
            
            if service_name and staff_name and key not in seen_services:
                seen_services.add(key)
                result.append({
                    "service_name": service_name,
                    "staff_name": staff_name
                })
        
        logger.info(f"   Returning {len(result)} service/staff combinations")
        return result
    
    def get_services_by_staff_name(self, staff_name: str) -> List[Dict[str, Any]]:
        """
        Get services for a specific staff member by name.
        Returns full service info: service_id, service_name, staff_id, staff_name, seance_length, price
        
        Args:
            staff_name: Name of the staff member to search for
        """
        logger.info(f"📋 get_services_by_staff_name called: {staff_name}")
        all_services = self._get_cached_services()
        
        # Filter services by staff name (case-insensitive, partial match)
        matching_services = []
        for service in all_services:
            service_staff_name = service.get("Staff Name") or service.get("staff_name") or ""
            if staff_name.lower() in service_staff_name.lower():
                # Возвращаем полные данные для записи
                # Колонки: Name, service_id, staff_id, Length, Price, Staff Name
                matching_services.append({
                    "service_id": str(service.get("service_id") or service.get("Service ID") or ""),
                    "service_name": service.get("Name") or service.get("Service Name") or service.get("service_name") or "",
                    "staff_id": str(service.get("staff_id") or service.get("Staff ID") or ""),
                    "staff_name": service_staff_name,
                    "seance_length": int(service.get("Length") or service.get("Seance Length") or service.get("seance_length") or 3600),
                    "price": int(service.get("Price") or service.get("price") or 0)
                })
        
        logger.info(f"   Found {len(matching_services)} services for {staff_name}")
        return matching_services
    
    def get_services_by_name(self, service_name: str, staff_name: str = None) -> List[Dict[str, Any]]:
        """
        Get services by service name, optionally filtered by staff name.
        Returns full service info.
        
        Args:
            service_name: Name of the service to search for
            staff_name: Optional staff name to filter by
        """
        logger.info(f"📋 get_services_by_name called: service={service_name}, staff={staff_name}")
        all_services = self._get_cached_services()
        
        matching_services = []
        for service in all_services:
            # Колонки: Name, service_id, staff_id, Length, Price, Staff Name
            svc_name = service.get("Name") or service.get("Service Name") or service.get("service_name") or ""
            stf_name = service.get("Staff Name") or service.get("staff_name") or ""
            
            # Filter by service name (case-insensitive, partial match)
            if service_name.lower() in svc_name.lower():
                # Optionally filter by staff name
                if staff_name is None or staff_name.lower() in stf_name.lower():
                    matching_services.append({
                        "service_id": str(service.get("service_id") or service.get("Service ID") or ""),
                        "service_name": svc_name,
                        "staff_id": str(service.get("staff_id") or service.get("Staff ID") or ""),
                        "staff_name": stf_name,
                        "seance_length": int(service.get("Length") or service.get("Seance Length") or service.get("seance_length") or 3600),
                        "price": int(service.get("Price") or service.get("price") or 0)
                    })
        
        logger.info(f"   Found {len(matching_services)} matching services")
        return matching_services
    
    def get_staff_id_by_name(self, staff_name: str) -> Optional[str]:
        """
        Get staff ID by name.
        """
        all_staff = self._get_cached_staff()
        
        for staff in all_staff:
            name = staff.get("name") or staff.get("Name") or staff.get("staff_name") or ""
            if staff_name.lower() in name.lower():
                return staff.get("staff_id") or staff.get("Staff ID") or staff.get("id")
        
        return None
    
    def get_service_info(
        self, 
        staff_name: str, 
        service_name: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get service information including service_id, seance_length, and price.
        """
        services = self.get_services_by_staff_name(staff_name)
        
        if not services:
            return None
        
        if service_name:
            for service in services:
                if service_name.lower() in service.get("service_name", "").lower():
                    return service
        
        # Return first service if no specific service requested
        return services[0] if services else None
    
    def find_best_match(self, query: str, search_type: str = "staff") -> Optional[Dict[str, Any]]:
        """
        Find best matching staff or service by name.
        Uses fuzzy matching to handle typos and variations.
        
        Args:
            query: Search query
            search_type: "staff" or "service"
        """
        query = query.lower().strip()
        
        if search_type == "staff":
            all_records = self._get_cached_staff()
            name_key = lambda r: (r.get("name") or r.get("Name") or r.get("staff_name") or "").lower()
        else:
            all_records = self._get_cached_services()
            name_key = lambda r: (r.get("Service Name") or r.get("service_name") or "").lower()
        
        # Exact match
        for record in all_records:
            if query == name_key(record):
                return record
        
        # Partial match (query contained in name)
        for record in all_records:
            if query in name_key(record):
                return record
        
        # Partial match (name contained in query)
        for record in all_records:
            if name_key(record) and name_key(record) in query:
                return record
        
        return None


# Singleton instance
sheets_service = GoogleSheetsService()