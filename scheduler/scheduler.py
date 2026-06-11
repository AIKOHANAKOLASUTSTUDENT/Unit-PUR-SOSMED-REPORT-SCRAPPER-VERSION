from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from main import run_scrape_and_upload
from utils.logger import get_logger

logger = get_logger()


def schedule_monthly_job() -> None:
    scheduler = BlockingScheduler(timezone="Asia/Jakarta")
    trigger = CronTrigger(day=1, hour=1, minute=0)
    scheduler.add_job(run_scrape_and_upload, trigger, id="apbd_monthly_job", replace_existing=True)
    logger.info("Registered scheduler job for cron expression: 0 1 1 * *")
    scheduler.start()


if __name__ == "__main__":
    schedule_monthly_job()
