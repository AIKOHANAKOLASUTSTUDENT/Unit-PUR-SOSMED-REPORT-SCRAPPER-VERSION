"""
Main orchestration script for Instagram Engagement Scraper.
Coordinates scraping, transformation, validation, and upload.
"""

from config.settings import SCRAPER_STRATEGY
from scraper.instagram_scraper import InstagramScraper
from transformer.processor import process_record
from transformer.validator import validate_record
from services.spreadsheet_service import SpreadsheetService
from utils.logger import get_logger


def read_urls(filepath: str) -> list[str]:
    """
    Read Instagram URLs from input file.
    
    Args:
        filepath: Path to file containing URLs (one per line)
    
    Returns:
        List of cleaned URLs
    """
    urls = []
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                # Skip blank lines and comments
                if not line or line.startswith("#"):
                    continue
                urls.append(line)
    except FileNotFoundError:
        raise FileNotFoundError(f"Input file not found: {filepath}")
    
    return urls


def main():
    """Main scraper orchestration."""
    logger = get_logger()
    logger.info("=== Instagram Engagement Scraper started ===")
    
    try:
        # Step 1: Read URLs
        logger.info("Step 1: Reading URLs from input/urls.txt")
        urls = read_urls("input/urls.txt")
        
        if not urls:
            logger.error("No URLs found in input/urls.txt. Exiting.")
            return
        
        logger.info(f"Loaded {len(urls)} URLs from input/urls.txt")
        
        # Step 2: Scrape
        logger.info(f"Step 2: Scraping with strategy '{SCRAPER_STRATEGY}'")
        scraper = InstagramScraper(strategy=SCRAPER_STRATEGY)
        raw_records = scraper.scrape(urls)
        logger.info(f"Scraped {len(raw_records)} records")
        
        # Step 3: Transform
        logger.info("Step 3: Transforming records")
        processed = [process_record(r) for r in raw_records]
        logger.info(f"Processed {len(processed)} records")
        
        # Step 4: Validate
        logger.info("Step 4: Validating records")
        valid_records = []
        for record in processed:
            ok, reason = validate_record(record)
            if ok:
                valid_records.append(record)
            else:
                logger.warning(f"Skipping invalid record: {reason} | URL: {record.get('url')}")
        
        logger.info(f"{len(valid_records)}/{len(processed)} records passed validation")
        
        if not valid_records:
            logger.warning("No valid records to upload")
            return
        
        # Step 5: Upload to Google Sheets
        logger.info("Step 5: Uploading to Google Sheets")
        service = SpreadsheetService()
        service.ensure_header()
        appended = service.append_rows(valid_records)
        logger.info(f"Upload complete. {appended} new rows added to Google Sheets.")
        
        logger.info("=== Scraper finished successfully ===")
    
    except Exception as e:
        logger.exception(f"Error occurred: {e}")
        raise


if __name__ == "__main__":
    main()
