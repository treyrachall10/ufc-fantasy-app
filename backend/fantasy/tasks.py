from celery import shared_task
from .models import Draft, DraftOrder
from django.db import transaction
import logging

logger = logging.getLogger(__name__)

AUTODRAFT_DELAY_SECONDS = 60

@shared_task
def execute_autodraft_check(draft_id, expected_pick):
    try:
        with transaction.atomic():
            try: 
                draft = Draft.objects.select_for_update().get(id=draft_id)
            except Draft.DoesNotExist:
                logger.error(f"Draft {draft_id} not found.")
                return
            # Checks if pick was already made
            if draft.current_pick != expected_pick:
                logger.info(f"Pick {expected_pick} already made. Skipping.")
                return
            
            from api.utils import autopick_fighter, execute_draft_pick

            try:
                # Looks up team that has current pick
                draft_order = DraftOrder.objects.get(draft=draft, pick_num=draft.current_pick)
                team = draft_order.team
            except DraftOrder.DoesNotExist:
                logger.error(f"No DraftOrder found for pick {draft.current_pick} in draft {draft_id}.")
                return

            # Autopicks fighter
            fighter, slot_type = autopick_fighter(team, draft)
            if not fighter:
                logger.warning(f"No available fighters for team {team.id} in draft {draft_id}.")
                return

            # Saves pick to db  
            execute_draft_pick(team, fighter, slot_type, draft, draft.current_pick)
            logger.info(f"AUTODRAFT: Pick {expected_pick} in Draft {draft_id} -> {fighter.full_name}")

    except Exception as e:
        logger.error(f"Autodraft error: {e}")
