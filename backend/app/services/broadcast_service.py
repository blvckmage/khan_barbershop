"""
Broadcast Service for automated WhatsApp notifications.
Handles:
- 1 hour before appointment reminders
- 20 days revisit reminders
- NPS collection (~1 hour after appointment ends)
- Background job scheduling
- Duplicate sending prevention

Bug fixes applied:
  1. has_notification_been_sent / add_notification_log are SYNC — removed incorrect await.
  2. Naive/aware datetime comparison fixed in alteegio_service.get_appointments_for_period.
  3. NPS window corrected: appointments started 1.5–2.5h ago (not 2–4h), so the
     client has ~just left the chair for a typical 1h haircut.
  4. check_revisit_reminders: replaced per-client 29-call loop with a single
     get_clients_with_future_appointments() batch call (14 API calls total).
"""
import logging
import asyncio
from datetime import datetime, timedelta, timezone
from typing import Optional
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from app.config import get_settings
from app.services.whatsapp_service import whatsapp_service
from app.services.alteegio_service import alteegio_service
from app.database import (
    add_notification_log, has_notification_been_sent, get_reminder_settings,
    cleanup_old_data,
)

settings = get_settings()
logger = logging.getLogger(__name__)

ALMATY_TZ = timezone(timedelta(hours=5))


class BroadcastService:
    """Service for managing automated broadcasts and notifications"""

    def __init__(self):
        self.scheduler: Optional[AsyncIOScheduler] = None
        self.is_running = False

    async def start(self):
        """Start background scheduler with periodic jobs"""
        if self.is_running:
            logger.info("⚠️ BroadcastService already running")
            return

        logger.info("🚀 Starting BroadcastService scheduler")

        self.scheduler = AsyncIOScheduler(timezone=ALMATY_TZ)

        # Check for upcoming appointments every 5 minutes
        self.scheduler.add_job(
            self.check_upcoming_appointments,
            trigger=IntervalTrigger(minutes=5),
            id='check_upcoming_appointments',
            replace_existing=True
        )

        # Check for revisit reminders once per day at 12:00
        self.scheduler.add_job(
            self.check_revisit_reminders,
            trigger='cron',
            hour=12,
            minute=0,
            id='check_revisit_reminders',
            replace_existing=True
        )

        # Check for completed appointments for NPS every 30 minutes
        self.scheduler.add_job(
            self.check_nps_collection,
            trigger=IntervalTrigger(minutes=30),
            id='check_nps_collection',
            replace_existing=True
        )

        # Check for scheduled broadcasts every 1 minute
        self.scheduler.add_job(
            self.check_scheduled_broadcasts,
            trigger=IntervalTrigger(minutes=1),
            id='check_scheduled_broadcasts',
            replace_existing=True
        )

        # Daily cleanup of old logs / webhook dedup at 03:00 Almaty
        self.scheduler.add_job(
            self.cleanup_job,
            trigger='cron',
            hour=3,
            minute=0,
            id='cleanup_old_data',
            replace_existing=True
        )

        self.scheduler.start()
        self.is_running = True
        logger.info("✅ BroadcastService scheduler started successfully")

    async def stop(self):
        """Stop background scheduler"""
        if self.scheduler:
            self.scheduler.shutdown()
            self.is_running = False
            logger.info("🛑 BroadcastService scheduler stopped")

    # ── 1-hour reminder ───────────────────────────────────────────────────────

    async def check_upcoming_appointments(self):
        """Check appointments starting in 55–65 minutes and send 1-hour reminders."""
        # Per-reminder kill-switch from admin panel
        if not get_reminder_settings().get('enable_one_hour_reminder', True):
            logger.info("🔕 1-hour reminders disabled in admin settings — skipping")
            return

        logger.info("🔍 Checking for upcoming appointments (1-hour reminders)")

        try:
            now = datetime.now(ALMATY_TZ)
            target_time = now + timedelta(hours=1)

            appointments = await alteegio_service.get_appointments_for_period(
                start_time=target_time - timedelta(minutes=5),
                end_time=target_time + timedelta(minutes=5)
            )

            if not appointments:
                logger.info("✅ No upcoming appointments found")
                return

            logger.info(f"📋 Found {len(appointments)} appointments in 1-hour window")

            sent_count = 0
            for appointment in appointments:
                try:
                    appointment_id = str(appointment.get('id', ''))
                    client_phone = appointment.get('client_phone', '')
                    client_name = appointment.get('client_name', 'Клиент')
                    master_name = appointment.get('master_name', 'Мастер')
                    appointment_time = appointment.get('datetime', '')

                    if not appointment_id or not client_phone:
                        continue

                    # FIX #1: has_notification_been_sent is SYNC — no await
                    if has_notification_been_sent(appointment_id, 'one_hour_reminder'):
                        logger.info(f"⏭️  Reminder already sent for appointment {appointment_id}")
                        continue

                    result = await whatsapp_service.send_one_hour_reminder(
                        to=client_phone,
                        client_name=client_name,
                        master_name=master_name,
                        datetime_str=appointment_time
                    )

                    # FIX #1: add_notification_log is SYNC — no await
                    if 'error' not in result:
                        add_notification_log(
                            appointment_id=appointment_id,
                            phone=client_phone,
                            type='one_hour_reminder',
                            message_sid=result.get('sid'),
                            status='sent',
                            master_name=master_name,
                            client_name=client_name,
                        )
                        sent_count += 1
                        logger.info(f"✅ 1-hour reminder sent to {client_phone}")
                    else:
                        add_notification_log(
                            appointment_id=appointment_id,
                            phone=client_phone,
                            type='one_hour_reminder',
                            status='failed',
                            error=result.get('error'),
                            master_name=master_name,
                            client_name=client_name,
                        )

                    await asyncio.sleep(1.5)

                except Exception as e:
                    logger.error(f"❌ Error processing appointment {appointment.get('id')}: {e}", exc_info=True)
                    continue

            logger.info(f"✅ 1-hour reminders done: {sent_count}/{len(appointments)} sent")

        except Exception as e:
            logger.error(f"❌ Error in check_upcoming_appointments: {e}", exc_info=True)

    # ── Revisit reminder (20 days) ────────────────────────────────────────────

    async def check_revisit_reminders(self):
        """Check clients who visited exactly 20 days ago and send revisit reminders."""
        if not get_reminder_settings().get('enable_revisit_reminder', True):
            logger.info("🔕 Revisit reminders disabled in admin settings — skipping")
            return

        logger.info("🔍 Checking for revisit reminders (20 days after last visit)")

        try:
            target_date = datetime.now(ALMATY_TZ).date() - timedelta(days=20)

            appointments = await alteegio_service.get_past_appointments_for_date(target_date)

            if not appointments:
                logger.info("✅ No past appointments found for 20 days ago")
                return

            logger.info(f"📋 Found {len(appointments)} appointments from 20 days ago")

            # FIX #4: batch-fetch phones with future bookings ONCE (14 API calls total)
            # instead of calling client_has_future_appointment() per client (N×14 calls).
            future_phones = await alteegio_service.get_clients_with_future_appointments(days_ahead=14)

            sent_count = 0
            for appointment in appointments:
                try:
                    appointment_id = str(appointment.get('id', ''))
                    client_phone = appointment.get('client_phone', '')
                    client_name = appointment.get('client_name', 'Клиент')
                    visit_date = appointment.get('datetime', str(target_date))

                    if not appointment_id or not client_phone:
                        continue

                    # FIX #1: sync — no await
                    if has_notification_been_sent(appointment_id, 'revisit_reminder'):
                        logger.info(f"⏭️  Revisit reminder already sent for {appointment_id}")
                        continue

                    # FIX #4: use batch result — O(len(future_phones)) instead of 14 API calls
                    has_future = any(
                        client_phone in p or p in client_phone
                        for p in future_phones
                    )

                    if has_future:
                        logger.info(f"⏭️  Client {client_phone} has future appointment — skipping")
                        # FIX #1: sync — no await
                        add_notification_log(
                            appointment_id=appointment_id,
                            phone=client_phone,
                            type='revisit_reminder',
                            status='skipped',
                            note='Client already has future appointment',
                            client_name=client_name,
                        )
                        continue

                    result = await whatsapp_service.send_revisit_reminder(
                        to=client_phone,
                        client_name=client_name,
                        last_visit_date=visit_date
                    )

                    # FIX #1: sync — no await
                    if 'error' not in result:
                        add_notification_log(
                            appointment_id=appointment_id,
                            phone=client_phone,
                            type='revisit_reminder',
                            message_sid=result.get('sid'),
                            status='sent',
                            client_name=client_name,
                        )
                        sent_count += 1
                        logger.info(f"✅ Revisit reminder sent to {client_phone}")
                    else:
                        add_notification_log(
                            appointment_id=appointment_id,
                            phone=client_phone,
                            type='revisit_reminder',
                            status='failed',
                            error=result.get('error'),
                            client_name=client_name,
                        )

                    await asyncio.sleep(1.5)

                except Exception as e:
                    logger.error(f"❌ Error processing revisit reminder: {e}", exc_info=True)
                    continue

            logger.info(f"✅ Revisit reminders done: {sent_count}/{len(appointments)} sent")

        except Exception as e:
            logger.error(f"❌ Error in check_revisit_reminders: {e}", exc_info=True)

    # ── NPS collection ────────────────────────────────────────────────────────

    async def check_nps_collection(self):
        """Send NPS request approximately 1 hour after the appointment ends.

        FIX #3: Corrected time window.
        Old window: appointments that started 2–4h ago → client still in the chair.
        New window: appointments that started 1.5–2.5h ago → for a typical ~1h haircut
        the client finished 0.5–1.5h ago, which is the right moment to ask for a rating.
        Deduplication via notification_logs prevents duplicate NPS messages.
        """
        if not get_reminder_settings().get('enable_nps_request', True):
            logger.info("🔕 NPS requests disabled in admin settings — skipping")
            return

        logger.info("🔍 Checking for NPS collection")

        try:
            now = datetime.now(ALMATY_TZ)
            # FIX #3: window centred at "2 hours ago" with ±30 min tolerance
            appointments = await alteegio_service.get_appointments_for_period(
                start_time=now - timedelta(hours=2, minutes=30),
                end_time=now - timedelta(hours=1, minutes=30)
            )

            if not appointments:
                return

            for appointment in appointments:
                try:
                    appointment_id = str(appointment.get('id', ''))
                    client_phone = appointment.get('client_phone', '')
                    client_name = appointment.get('client_name', 'Клиент')
                    master_name = appointment.get('master_name', 'Мастер')

                    if not appointment_id or not client_phone:
                        continue

                    # FIX #1: sync — no await
                    if has_notification_been_sent(appointment_id, 'nps_request'):
                        continue

                    result = await whatsapp_service.send_nps_request(
                        to=client_phone,
                        client_name=client_name,
                        master_name=master_name
                    )

                    # FIX #1: sync — no await
                    # NPS notification log MUST include master_name + client_name
                    # so the incoming rating can be linked to the right master.
                    if 'error' not in result:
                        add_notification_log(
                            appointment_id=appointment_id,
                            phone=client_phone,
                            type='nps_request',
                            message_sid=result.get('sid'),
                            status='sent',
                            master_name=master_name,
                            client_name=client_name,
                        )
                        logger.info(f"✅ NPS request sent to {client_phone}")
                    else:
                        add_notification_log(
                            appointment_id=appointment_id,
                            phone=client_phone,
                            type='nps_request',
                            status='failed',
                            error=result.get('error'),
                            master_name=master_name,
                            client_name=client_name,
                        )
                    await asyncio.sleep(1.5)
                except Exception as e:
                    logger.error(f"❌ Error processing NPS for {appointment.get('id')}: {e}")
                    continue
        except Exception as e:
            logger.error(f"❌ Error in check_nps_collection: {e}")

    # ── Daily cleanup ─────────────────────────────────────────────────────────

    async def cleanup_job(self):
        """Delete old logs / webhook dedup rows. Keeps DB size bounded."""
        try:
            log_days = settings.log_retention_days
            webhook_hours = settings.webhook_dedup_retention_hours
            logger.info(f"🧹 Running cleanup: logs > {log_days}d, webhook_dedup > {webhook_hours}h")
            deleted = cleanup_old_data(log_days=log_days, webhook_hours=webhook_hours)
            logger.info(f"🧹 Cleanup done: {deleted}")
        except Exception as e:
            logger.error(f"❌ Cleanup job error: {e}", exc_info=True)

    # ── Scheduled broadcasts ──────────────────────────────────────────────────

    async def check_scheduled_broadcasts(self):
        """Check and execute scheduled broadcasts"""
        from app.database import get_due_scheduled_broadcasts, update_broadcast_summary, add_broadcast_log
        import json

        logger.info("🔍 Checking for due scheduled broadcasts")
        now_str = datetime.now(ALMATY_TZ).strftime("%Y-%m-%dT%H:%M:%S")

        try:
            broadcasts = get_due_scheduled_broadcasts(now_str)
            for b in broadcasts:
                broadcast_id = b['id']
                message = b['message']
                recipients = json.loads(b['recipients'] or '[]')

                sent_count = 0
                failed_count = 0

                for recipient in recipients:
                    try:
                        result = await whatsapp_service.send_whatsapp_message(recipient, message)
                        if 'error' in result:
                            failed_count += 1
                            add_broadcast_log(broadcast_id, recipient, None, 'failed', result.get('error'))
                        else:
                            sent_count += 1
                            add_broadcast_log(broadcast_id, recipient, result.get('sid'), 'sent')
                    except Exception as e:
                        failed_count += 1
                        add_broadcast_log(broadcast_id, recipient, None, 'failed', str(e))
                    finally:
                        await asyncio.sleep(1)

                status = (
                    'completed' if sent_count > 0 and failed_count == 0
                    else 'failed' if sent_count == 0
                    else 'completed'
                )
                update_broadcast_summary(
                    broadcast_id, sent_count, failed_count, status,
                    datetime.now(ALMATY_TZ).isoformat()
                )

        except Exception as e:
            logger.error(f"❌ Error in check_scheduled_broadcasts: {e}")


# Singleton instance
broadcast_service = BroadcastService()
