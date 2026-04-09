"""
Broadcast Service for automated WhatsApp notifications.
Handles:
- 1 hour before appointment reminders
- 20 days revisit reminders
- Background job scheduling
- Duplicate sending prevention
"""
import logging
import asyncio
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from app.config import get_settings
from app.services.twilio_service import twilio_service
from app.services.alteegio_service import alteegio_service
from app.database import add_notification_log, has_notification_been_sent

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
        
        self.scheduler.start()
        self.is_running = True
        logger.info("✅ BroadcastService scheduler started successfully")
        
    async def stop(self):
        """Stop background scheduler"""
        if self.scheduler:
            self.scheduler.shutdown()
            self.is_running = False
            logger.info("🛑 BroadcastService scheduler stopped")
            
    async def check_upcoming_appointments(self):
        """Check appointments that will start in 55-65 minutes and send reminders"""
        logger.info("🔍 Checking for upcoming appointments (1 hour reminders)")
        
        try:
            now = datetime.now(ALMATY_TZ)
            target_time = now + timedelta(hours=1)
            
            # Get appointments for the next hour
            appointments = await alteegio_service.get_appointments_for_period(
                start_time=target_time - timedelta(minutes=5),
                end_time=target_time + timedelta(minutes=5)
            )
            
            if not appointments:
                logger.info("✅ No upcoming appointments found")
                return
                
            logger.info(f"📋 Found {len(appointments)} appointments in 1 hour window")
            
            sent_count = 0
            for appointment in appointments:
                try:
                    appointment_id = appointment.get('id')
                    client_phone = appointment.get('client_phone')
                    client_name = appointment.get('client_name', 'Клиент')
                    master_name = appointment.get('master_name', 'Мастер')
                    appointment_time = appointment.get('datetime')
                    
                    # Skip if already sent
                    if await has_notification_been_sent(appointment_id, 'one_hour_reminder'):
                        logger.info(f"⏭️  Reminder already sent for appointment {appointment_id}")
                        continue
                        
                    # Send reminder
                    result = await twilio_service.send_one_hour_reminder(
                        to=client_phone,
                        client_name=client_name,
                        master_name=master_name,
                        datetime_str=appointment_time
                    )
                    
                    if 'error' not in result:
                        await add_notification_log(
                            appointment_id=appointment_id,
                            phone=client_phone,
                            type='one_hour_reminder',
                            message_sid=result.get('sid'),
                            status='sent'
                        )
                        sent_count += 1
                        logger.info(f"✅ 1 hour reminder sent to {client_phone}")
                    else:
                        await add_notification_log(
                            appointment_id=appointment_id,
                            phone=client_phone,
                            type='one_hour_reminder',
                            status='failed',
                            error=result.get('error')
                        )
                        
                    # Add delay to respect Twilio rate limits
                    await asyncio.sleep(1.5)
                    
                except Exception as e:
                    logger.error(f"❌ Error processing appointment: {e}", exc_info=True)
                    continue
                    
            logger.info(f"✅ Completed upcoming appointments check: {sent_count}/{len(appointments)} reminders sent")
            
        except Exception as e:
            logger.error(f"❌ Error in check_upcoming_appointments: {e}", exc_info=True)
            
    async def check_revisit_reminders(self):
        """Check clients who visited exactly 20 days ago and send revisit reminders"""
        logger.info("🔍 Checking for revisit reminders (20 days after last visit)")
        
        try:
            target_date = datetime.now(ALMATY_TZ).date() - timedelta(days=20)
            
            # Get all appointments from 20 days ago
            appointments = await alteegio_service.get_past_appointments_for_date(target_date)
            
            if not appointments:
                logger.info("✅ No past appointments found for 20 days ago")
                return
                
            logger.info(f"📋 Found {len(appointments)} appointments from 20 days ago")
            
            sent_count = 0
            for appointment in appointments:
                try:
                    appointment_id = appointment.get('id')
                    client_phone = appointment.get('client_phone')
                    client_name = appointment.get('client_name', 'Клиент')
                    visit_date = appointment.get('datetime', str(target_date))
                    
                    # Skip if already sent
                    if await has_notification_been_sent(appointment_id, 'revisit_reminder'):
                        logger.info(f"⏭️  Revisit reminder already sent for appointment {appointment_id}")
                        continue
                        
                    # Check if client already has future appointment
                    has_future = await alteegio_service.client_has_future_appointment(client_phone)
                    if has_future:
                        logger.info(f"⏭️  Client {client_phone} already has future appointment, skipping")
                        await add_notification_log(
                            appointment_id=appointment_id,
                            phone=client_phone,
                            type='revisit_reminder',
                            status='skipped',
                            note='Client already has future appointment'
                        )
                        continue
                        
                    # Send revisit reminder
                    result = await twilio_service.send_revisit_reminder(
                        to=client_phone,
                        client_name=client_name,
                        last_visit_date=visit_date
                    )
                    
                    if 'error' not in result:
                        await add_notification_log(
                            appointment_id=appointment_id,
                            phone=client_phone,
                            type='revisit_reminder',
                            message_sid=result.get('sid'),
                            status='sent'
                        )
                        sent_count += 1
                        logger.info(f"✅ Revisit reminder sent to {client_phone}")
                    else:
                        await add_notification_log(
                            appointment_id=appointment_id,
                            phone=client_phone,
                            type='revisit_reminder',
                            status='failed',
                            error=result.get('error')
                        )
                        
                    # Add delay to respect Twilio rate limits
                    await asyncio.sleep(1.5)
                    
                except Exception as e:
                    logger.error(f"❌ Error processing revisit reminder: {e}", exc_info=True)
                    continue
                    
            logger.info(f"✅ Completed revisit reminders check: {sent_count}/{len(appointments)} reminders sent")
            
        except Exception as e:
            logger.error(f"❌ Error in check_revisit_reminders: {e}", exc_info=True)


# Singleton instance
broadcast_service = BroadcastService()