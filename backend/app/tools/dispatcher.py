from app.tools.booking_tool import BookingTool
from app.tools.all_staff_tool import AllStaffTool
from app.services.alteegio_service import alteegio_service
from app.services.sheets_service import sheets_service
from app.tools.context_manager import RedisContextManager


ctx_manager = RedisContextManager()


async def dispatch_tool(tool_name: str, args: dict, session_id: str = None):
    """Dispatcher for available tools. Returns result or error dict."""
    try:
        if tool_name == "get_all_staff":
            return sheets_service.get_all_staff()

        if tool_name == "get_services_by_staff_name":
            res = sheets_service.get_services_by_staff_name(args["staff_name"])
            # update context with default service if called in session
            if session_id and res:
                ctx = ctx_manager.get_context(session_id) or {}
                ctx["staff_id"] = str(res[0].get("staff_id"))
                # pick default service
                default = None
                for svc in res:
                    if "стрижка" in (svc.get("service_name") or "").lower():
                        default = svc
                        break
                if not default:
                    default = res[0]
                if default:
                    ctx["service_id"] = str(default.get("service_id"))
                    ctx["seance_length"] = str(default.get("seance_length", 3600))
                ctx_manager.set_context(session_id, ctx)
            return res

        if tool_name == "get_services_by_name":
            return sheets_service.get_services_by_name(args.get("service_name"), args.get("staff_name"))

        if tool_name == "get_available_dates":
            return await alteegio_service.get_available_dates(args["staff_id"], args.get("service_ids", []))

        if tool_name == "get_available_times":
            # prefer context service_id
            service_ids = args.get("service_ids")
            if session_id and not service_ids:
                ctx = ctx_manager.get_context(session_id) or {}
                if ctx.get("service_id"):
                    service_ids = [ctx.get("service_id")]
            return await alteegio_service.get_available_times(args["staff_id"], args["date"], service_ids or [])

        if tool_name == "get_available_masters":
            masters = await alteegio_service.get_available_masters(args.get("datetime"))
            # handle multi-booking save
            if session_id and masters:
                ctx = ctx_manager.get_context(session_id) or {}
                multi_count = ctx.get("multi_booking_count", 1)
                if multi_count > 1:
                    staff_ids = [str(m.get("id")) for m in masters[:multi_count]]
                    ctx["multi_booking_staff_ids"] = staff_ids
                    ctx["datetime"] = args.get("datetime")
                    ctx["date"] = args.get("datetime", "").split("T")[0] if args.get("datetime") else None
                    ctx["waiting_for_name"] = True
                    # save default service if can detect from first master
                    services = sheets_service.get_services_by_staff_name(masters[0].get("name")) if masters and masters[0].get("name") else []
                    if services:
                        default = None
                        for svc in services:
                            if "стрижка" in (svc.get("service_name") or "").lower():
                                default = svc
                                break
                        if not default:
                            default = services[0]
                        if default:
                            ctx["service_id"] = str(default.get("service_id"))
                            ctx["seance_length"] = str(default.get("seance_length", 3600))
                ctx_manager.set_context(session_id, ctx)
            return masters

        if tool_name == "create_appointment":
            res = await alteegio_service.create_appointment(
                staff_id=args["staff_id"], service_id=args["service_id"],
                client_phone=args["client_phone"], client_name=args["client_name"],
                datetime=args["datetime"], seance_length=args.get("seance_length", "3600")
            )
            # clear booking context on success
            if session_id and isinstance(res, dict) and res.get("success"):
                ctx_manager.set_context(session_id, {
                    "staff_id": None, "service_id": None, "seance_length": None,
                    "datetime": None, "waiting_for_name": False,
                    "preferred_time": None, "requested_hour": None, "requested_minute": None, "date": None,
                    "multi_booking_count": 1, "bookings_created": 0,
                    "multi_booking_staff_ids": []
                })
            return res

        if tool_name == "get_all_staff":
            return sheets_service.get_all_staff()

        return {"error": f"Unknown tool: {tool_name}"}
    except Exception as e:
        return {"error": str(e)}
