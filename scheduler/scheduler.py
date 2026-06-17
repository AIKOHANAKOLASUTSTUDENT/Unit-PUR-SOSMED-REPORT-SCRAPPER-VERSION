import sys
from pathlib import Path

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from main import run_scrape_and_upload
from utils.logger import get_logger

logger = get_logger()


def schedule_monthly_job() -> None:
    scheduler = BlockingScheduler(timezone="Asia/Jakarta")
    # trigger = CronTrigger(day=1, hour=1, minute=0)
    trigger = CronTrigger(minute="1")
    scheduler.add_job(run_scrape_and_upload, trigger, id="apbd_monthly_job", replace_existing=True)
    # logger.info("Registered scheduler job for cron expression: 0 1 1 * *")
    logger.info("Registered scheduler job for cron expression: */1 * * * *")
    scheduler.start()


if __name__ == "__main__":
    schedule_monthly_job()
