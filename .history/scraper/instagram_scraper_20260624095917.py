"""
Instagram scraper module.
Implements two strategies: instaloader and playwright.
"""

import re
import time
from typing import Dict, List, Any, Optional

# Optional imports: try to import heavy/optional dependencies but don't fail at module import
try:
    import instaloader
    from instaloader.exceptions import (
        InstaloaderException,
        QueryReturnedNotFoundException,
        TwoFactorAuthRequiredException,
    )
    HAS_INSTALOADER = True
except Exception:
    instaloader = None
    InstaloaderException = Exception
    QueryReturnedNotFoundException = Exception
    TwoFactorAuthRequiredException = Exception
    HAS_INSTALOADER = False

try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
    HAS_PLAYWRIGHT = True
except Exception:
    sync_playwright = None
    PlaywrightTimeoutError = Exception
    HAS_PLAYWRIGHT = False

try:
    from bs4 import BeautifulSoup
    HAS_BS4 = True
except Exception:
    BeautifulSoup = None
    HAS_BS4 = False

from config.settings import (
    INSTAGRAM_USERNAME,
    INSTAGRAM_PASSWORD,
    REQUEST_DELAY_SECONDS,
    MAX_RETRIES,
)
from utils.logger import get_logger


DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)


class InstagramScraper:
    """
    Main scraper class with support for multiple strategies.
    """

    def __init__(self, strategy: str = "instaloader"):
        """
        Initialize scraper with specified strategy.
        
        Args:
            strategy: "instaloader" or "playwright"
        """
        self.logger = get_logger()
        self.strategy = strategy.lower()

        if self.strategy not in ["instaloader", "playwright"]:
            raise ValueError(f"Unknown strategy: {strategy}")

        # Fallback handling when optional libs are missing
        if self.strategy == "instaloader" and not HAS_INSTALOADER:
            self.logger.warning("Instaloader not available; attempting to fall back to Playwright.")
            if HAS_PLAYWRIGHT:
                self.strategy = "playwright"
            else:
                self.logger.warning("Neither instaloader nor playwright available. Scraper will run in noop mode.")
                self.strategy = "noop"

        if self.strategy == "instaloader":
            self._init_instaloader()
        elif self.strategy == "playwright":
            # Playwright will be initialized on-demand in _scrape_one_playwright
            pass
        else:
            # noop mode: methods will return N/A records
            pass
        
        self.logger.info(f"InstagramScraper initialized with strategy: {self.strategy}")
    
    def _init_instaloader(self):
        """Initialize instaloader client."""
        if not HAS_INSTALOADER:
            self.instaloader_client = None
            self.logger.warning("_instaloader_ package not available; skipping instaloader init.")
            return

        self.instaloader_client = instaloader.Instaloader(
            sleep=False,  # We handle sleep ourselves
            compress_json=False,
        )

        # Try to login if credentials provided
        login_success = False
        if INSTAGRAM_USERNAME and INSTAGRAM_PASSWORD:
            try:
                self.instaloader_client.login(INSTAGRAM_USERNAME, INSTAGRAM_PASSWORD)
                login_success = True
                self.logger.info(f"Logged in as {INSTAGRAM_USERNAME}")
            except TwoFactorAuthRequiredException:
                self.logger.error(
                    "Instagram login requires two-factor authentication. "
                    "Continuing without login."
                )
            except Exception as e:
                self.logger.warning(f"Failed to login to Instagram: {e}")
        else:
            self.logger.info("No Instagram credentials provided. Will only access public content.")

        self.logger.debug(f"Login success: {login_success}")
    
    def scrape(self, urls: List[str]) -> List[Dict[str, Any]]:
        """
        Scrape multiple URLs.
        
        Args:
            urls: List of Instagram URLs
        
        Returns:
            List of raw record dicts
        """
        self.logger.info(f"Starting scrape of {len(urls)} URLs with strategy: {self.strategy}")
        records = []
        
        for idx, url in enumerate(urls):
            try:
                record = self._scrape_one(url)
                records.append(record)
                self.logger.info(f"[{idx+1}/{len(urls)}] Scraped: {url}")
            except Exception as e:
                self.logger.error(f"Error scraping {url}: {e}")
                # Append N/A record
                records.append({
                    "url": url,
                    "content_type": "N/A",
                    "likes_raw": "N/A",
                    "comments_raw": "N/A",
                    "views_raw": "N/A",
                    "reposts_raw": "N/A",
                    "saves_raw": "N/A",
                    "shares_raw": "N/A",
                    "post_date_raw": "N/A",
                    "caption_raw": "N/A",
                })
            
            # Wait between requests (except after last one)
            if idx < len(urls) - 1:
                time.sleep(REQUEST_DELAY_SECONDS)
        
        self.logger.info(f"Scrape complete. Got {len(records)} records")
        return records
    
    def _scrape_one(self, url: str) -> Dict[str, Any]:
        """
        Scrape a single URL.
        
        Args:
            url: Instagram URL
        
        Returns:
            Raw record dict
        """
        lower_url = url.lower()

        if "/reel/" in lower_url:
            return self._scrape_one_instaloader(url)

        if "/p/" in lower_url:
            return self._scrape_playwright_single(url)

        if self.strategy == "playwright":
            return self._scrape_one_playwright(url)

        if self.strategy == "instaloader":
            return self._scrape_one_instaloader(url)

        return self._empty_record(url)

    def _empty_record(self, url: str) -> Dict[str, Any]:
        """Return an empty raw record with Post defaults."""
        return {
            "url": url,
            "content_type": "Post",
            "likes_raw": "N/A",
            "comments_raw": "N/A",
            "views_raw": "N/A",
            "reposts_raw": "N/A",
            "saves_raw": "N/A",
            "shares_raw": "N/A",
            "post_date_raw": "N/A",
            "caption_raw": "N/A",
        }

    def _scrape_playwright_single(self, url: str) -> Dict[str, Any]:
        """Scrape a single Instagram post page using Playwright."""
        record = self._empty_record(url)
        record["content_type"] = "Post"

        browser = None
        try:
            if not HAS_PLAYWRIGHT:
                self.logger.warning(f"Playwright not available for {url}; returning empty record")
                return record

            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    user_agent=(
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/124.0.0.0 Safari/537.36"
                    )
                )
                page = context.new_page()
                page.goto(url, wait_until="networkidle", timeout=30000)

                html_content = page.content()
                if HAS_BS4:
                    soup = BeautifulSoup(html_content, "html.parser")
                else:
                    soup = None

                if soup is None:
                    self.logger.warning("BeautifulSoup not available; cannot parse page HTML")
                    return record

                og_description = soup.select_one('meta[property="og:description"]')
                if og_description and og_description.get("content"):
                    description = og_description["content"]
                    likes_match = re.search(r"([\d,]+)\s+[Ll]ike", description)
                    comments_match = re.search(r"([\d,]+)\s+[Cc]omment", description)
                    if likes_match:
                        record["likes_raw"] = likes_match.group(1).replace(",", "")
                    if comments_match:
                        record["comments_raw"] = comments_match.group(1).replace(",", "")

                published_time = soup.select_one('meta[property="article:published_time"]')
                if published_time and published_time.get("content"):
                    record["post_date_raw"] = published_time["content"]

                og_title = soup.select_one('meta[property="og:title"]')
                if og_title and og_title.get("content"):
                    record["caption_raw"] = og_title["content"]

                og_video = soup.select_one('meta[property="og:video"]')
                og_video_url = soup.select_one('meta[property="og:video:url"]')
                og_images = soup.select('meta[property="og:image"]')

                if og_video or og_video_url:
                    record["content_type"] = "Reel"
                elif len(og_images) > 1:
                    record["content_type"] = "Carousel"
                else:
                    record["content_type"] = "Post"

                # Extract views from page text or meta
                views_text = []
                if og_description and og_description.get("content"):
                    views_text.append(og_description["content"])
                if og_title and og_title.get("content"):
                    views_text.append(og_title["content"])
                views_meta = soup.find_all(lambda tag: tag.name == "meta" and tag.get("content") and "views" in tag.get("content", "").lower())
                for meta in views_meta:
                    views_text.append(meta.get("content", ""))
                for span in soup.find_all("span"):
                    if span.text and "view" in span.text.lower():
                        views_text.append(span.text)

                for text in views_text:
                    if not text:
                        continue
                    views_match = re.search(r"([\d,]+)\s+[Vv]iew", text)
                    if views_match:
                        record["views_raw"] = views_match.group(1).replace(",", "")
                        break

                self.logger.debug(
                    "Playwright single scrape data: likes=%s comments=%s content_type=%s date=%s views=%s caption=%s",
                    record["likes_raw"],
                    record["comments_raw"],
                    record["content_type"],
                    record["post_date_raw"],
                    record["views_raw"],
                    record["caption_raw"],
                )

                context.close()
                browser.close()

        except Exception as e:
            self.logger.error(f"Playwright scrape failed for {url}: {e}")
            self.logger.exception(e)
            return self._empty_record(url)
        finally:
            if browser:
                try:
                    browser.close()
                except Exception:
                    pass

        return record

    def _scrape_one_instaloader(self, url: str) -> Dict[str, Any]:
        """
        Scrape using instaloader strategy.
        """
        record = {
            "url": url,
            "content_type": "Post",
            "likes_raw": "N/A",
            "comments_raw": "N/A",
            "views_raw": "N/A",
            "reposts_raw": "N/A",
            "saves_raw": "N/A",
            "shares_raw": "N/A",
            "post_date_raw": "N/A",
            "caption_raw": "N/A",
        }
        
        try:
            if not HAS_INSTALOADER or self.instaloader_client is None:
                self.logger.warning(f"Instaloader not available for {url}; returning N/A record")
                return record

            shortcode = self._extract_shortcode(url)
            post = instaloader.Post.from_shortcode(self.instaloader_client.context, shortcode)
            
            self.logger.debug(
                "Instaloader post loaded: likes=%s, comments=%s, typename=%s, is_video=%s, date_utc=%s",
                getattr(post, "likes", None),
                getattr(post, "comments", None),
                getattr(post, "typename", None),
                getattr(post, "is_video", None),
                getattr(post, "date_utc", None),
            )

            # Extract metrics
            record["likes_raw"] = post.likes
            record["comments_raw"] = post.comments
            record["views_raw"] = post.video_view_count if post.is_video else "N/A"
            record["post_date_raw"] = (
                post.date_utc.strftime("%Y-%m-%dT%H:%M:%S")
                if getattr(post, "date_utc", None) is not None
                else "N/A"
            )
            record["caption_raw"] = post.caption if post.caption is not None else ""
            
            # Determine content type
            if "/reel/" in url.lower() or post.is_video:
                record["content_type"] = "Reel"
            elif post.typename == "GraphSidecar":
                record["content_type"] = "Carousel"
            else:
                record["content_type"] = "Post"
            
            return record
        
        except (InstaloaderException, QueryReturnedNotFoundException) as e:
            self.logger.warning(f"Instaloader error for {url}: {e}")
            self.logger.exception(e)
            return record
        except Exception as e:
            self.logger.error(f"Unexpected error in instaloader for {url}: {e}")
            self.logger.exception(e)
            return record
    
    def _scrape_one_playwright(self, url: str) -> Dict[str, Any]:
        """
        Scrape using playwright strategy (fallback).
        """
        record = {
            "url": url,
            "content_type": "Post",
            "likes_raw": "N/A",
            "comments_raw": "N/A",
            "views_raw": "N/A",
            "reposts_raw": "N/A",
            "saves_raw": "N/A",
            "shares_raw": "N/A",
            "post_date_raw": "N/A",
            "caption_raw": "N/A",
        }
        
        browser = None
        try:
            if not HAS_PLAYWRIGHT:
                self.logger.warning(f"Playwright not available for {url}; returning N/A record")
                return record

            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(user_agent=DEFAULT_USER_AGENT)
                page = context.new_page()
                
                page.goto(url, wait_until="networkidle", timeout=30000)
                
                # Get HTML content
                html_content = page.content()
                if HAS_BS4:
                    soup = BeautifulSoup(html_content, "html.parser")
                else:
                    soup = None
                
                # Try to extract data from meta tags
                if soup is not None:
                    og_description = soup.select_one('meta[property="og:description"]')
                    if og_description:
                        description = og_description.get("content", "")
                        record["caption_raw"] = description
                
                # Try to find engagement numbers in page
                # Look for common patterns like "X Likes, Y Comments"
                page_text = page.inner_text()
                
                # Extract numbers from various patterns
                likes_match = re.search(r'([\d,]+)\s*(?:like|♥)', page_text, re.IGNORECASE)
                if likes_match:
                    record["likes_raw"] = likes_match.group(1).replace(",", "")
                
                comments_match = re.search(r'([\d,]+)\s*comment', page_text, re.IGNORECASE)
                if comments_match:
                    record["comments_raw"] = comments_match.group(1).replace(",", "")
                
                views_match = re.search(r'([\d,]+)\s*view', page_text, re.IGNORECASE)
                if views_match:
                    record["views_raw"] = views_match.group(1).replace(",", "")
                
                # Determine content type from URL
                if "/reel/" in url.lower():
                    record["content_type"] = "Reel"
                elif "/p/" in url.lower():
                    record["content_type"] = "Post"
                else:
                    record["content_type"] = "Unknown"
                
                context.close()
                browser.close()
                
        except PlaywrightTimeoutError:
            self.logger.warning(f"Playwright timeout for {url}")
        except Exception as e:
            self.logger.error(f"Playwright error for {url}: {e}")
        finally:
            if browser:
                try:
                    browser.close()
                except:
                    pass
        
        return record
    
    @staticmethod
    def _extract_shortcode(url: str) -> str:
        """
        Extract Instagram shortcode from URL.
        
        Args:
            url: Instagram post/reel URL
        
        Returns:
            Shortcode string
            
        Raises:
            ValueError: If URL format is invalid
        """
        # Handle both /p/SHORTCODE/ and /reel/SHORTCODE/ formats
        match = re.search(r'(?:/p/|/reel/)([A-Za-z0-9_-]+)', url)
        if not match:
            raise ValueError(f"Could not extract shortcode from URL: {url}")
        
        return match.group(1)
