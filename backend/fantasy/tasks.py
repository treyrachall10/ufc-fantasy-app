from celery import shared_task
from .models import Draft, DraftOrder
from django.db import transaction
import logging

logger = logging.getLogger(__name__)

AUTODRAFT_DELAY_SECONDS = 60

@shared_task
def execute_autodraft_check(draft_id, expected_pick):
    try:
        # STEP 1: PRE-CALCULATE THE PICK EARLY (No database locks)
        try: 
            draft = Draft.objects.get(id=draft_id)
        except Draft.DoesNotExist:
            logger.error(f"Draft {draft_id} not found.")
            return
            
        if draft.current_pick != expected_pick:
            logger.info(f"Pick {expected_pick} already made. Skipping pre-calculation.")
            return
            
        from api.utils import autopick_fighter, execute_draft_pick
        
        try:
            draft_order = DraftOrder.objects.get(draft=draft, pick_num=draft.current_pick)
            team = draft_order.team
        except DraftOrder.DoesNotExist:
            logger.error(f"No DraftOrder found for pick {draft.current_pick} in draft {draft_id}.")
            return
            
        # Calculate the best fighter (This takes ~1.5 seconds)
        fighter, slot_type = autopick_fighter(team, draft)
        if not fighter:
            logger.warning(f"No available fighters for team {team.id} in draft {draft_id}.")
            return

        # STEP 2: STANDBY / SLEEP UNTIL EXACTLY 60 SECONDS
        import time
        from django.utils import timezone
        from datetime import timedelta
        
        # We need the freshest start time to calculate the sleep
        draft.refresh_from_db()
        if draft.current_pick != expected_pick:
            return
            
        target_time = draft.pick_start_time + timedelta(seconds=60)
        now = timezone.now()
        sleep_seconds = (target_time - now).total_seconds()
        
        # If the worker arrived early (e.g. at 50 seconds), sleep for the remaining time
        if sleep_seconds > 0:
            time.sleep(sleep_seconds)
            
        # STEP 3: EXECUTE INSTANTLY AT T=60s WITH LOCKS
        with transaction.atomic():
            draft = Draft.objects.select_for_update().get(id=draft_id)
            
            # Final verify right at 00:00! If a human picked during our sleep, we throw it away.
            if draft.current_pick != expected_pick:
                logger.info(f"Human picked during standby for pick {expected_pick}. Throwing away autodraft.")
                return
                
            # Execute the pick!
            execute_draft_pick(team, fighter, slot_type, draft, draft.current_pick)
            logger.info(f"AUTODRAFT: Pick {expected_pick} in Draft {draft_id} -> {fighter.full_name}")

    except Exception as e:
        logger.error(f"Autodraft error: {e}")
