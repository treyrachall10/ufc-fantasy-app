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

            if draft.current_pick != expected_pick:
                logger.info(f"Pick {expected_pick} already made. Skipping.")
                return

            logger.info(f"Draft {draft_id}: Pick {expected_pick} timed out. Autodraft not yet implemented.")

    except Exception as e:
        logger.error(f"Autodraft error: {e}")
