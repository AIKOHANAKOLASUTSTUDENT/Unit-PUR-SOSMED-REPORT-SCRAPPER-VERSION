"""
Streamlit web dashboard for Instagram Engagement Scraper.
Provides a user-friendly interface for scraping Instagram URLs without coding.
"""

import streamlit as st
import pandas as pd
import re
from typing import List
from config.settings import SCRAPER_STRATEGY, GOOGLE_SHEET_ID
from scraper.instagram_scraper import InstagramScraper
from transformer.processor import process_record
from transformer.validator import validate_record
from services.spreadsheet_service import SpreadsheetService
from utils.logger import get_logger

# Page config - MUST be first Streamlit call
st.set_page_config(
    page_title="Instagram Engagement Report",
    page_icon="📊",
    layout="wide"
)

# Initialize session state
if "has_results" not in st.session_state:
    st.session_state["has_results"] = False
if "results" not in st.session_state:
    st.session_state["results"] = []
if "invalid" not in st.session_state:
    st.session_state["invalid"] = []
if "appended_count" not in st.session_state:
    st.session_state["appended_count"] = 0

logger = get_logger()


def parse_urls(input_text: str) -> List[str]:
    """
    Parse and validate Instagram URLs from input text.
    Splits by comma, newline, and whitespace.
    Deduplicates while preserving order.
    """
    if not input_text.strip():
        return []
    
    # Split by comma, newline, and multiple whitespace
    urls = re.split(r'[,\n\s]+', input_text.strip())
    
    # Filter valid Instagram URLs and deduplicate
    valid_urls = []
    seen = set()
    for url in urls:
        url = url.strip()
        if url.startswith("https://www.instagram.com/") and url not in seen:
            valid_urls.append(url)
            seen.add(url)
    
    return valid_urls


def calculate_metrics(results: List[dict]) -> dict:
    """Calculate summary metrics from results."""
    total_likes = sum([r.get("likes", 0) if isinstance(r.get("likes"), int) else 0 for r in results])
    total_comments = sum([r.get("comments", 0) if isinstance(r.get("comments"), int) else 0 for r in results])
    total_views = sum([r.get("views", 0) if isinstance(r.get("views"), int) else 0 for r in results])
    
    return {
        "total_urls": len(results),
        "total_likes": total_likes,
        "total_comments": total_comments,
        "total_views": total_views,
    }


# ============================================================================
# MAIN APP
# ============================================================================

# Page title
st.title("📊 Instagram Engagement Report")

# ============================================================================
# SECTION 1: URL INPUT AREA
# ============================================================================

st.header("📥 Input URL Instagram")

url_input = st.text_area(
    "Masukkan URL Instagram (pisahkan dengan koma, spasi, atau baris baru)",
    height=160,
    placeholder="https://www.instagram.com/p/ABC123/\nhttps://www.instagram.com/reel/XYZ789/"
)

# Parse URLs
parsed_urls = parse_urls(url_input)
st.caption(f"✅ {len(parsed_urls)} URL valid ditemukan")

# Input buttons
col1, col2 = st.columns([2, 1])

with col1:
    scrape_clicked = st.button("🚀 Mulai Scraping", use_container_width=True, type="primary")

with col2:
    reset_clicked = st.button("🗑️ Reset", use_container_width=True)

# Reset button logic
if reset_clicked:
    for key in ["has_results", "results", "invalid", "appended_count"]:
        if key in st.session_state:
            del st.session_state[key]
    st.rerun()

# ============================================================================
# SECTION 2: PROGRESS & STATUS (shown only while scraping)
# ============================================================================

if scrape_clicked and len(parsed_urls) > 0:
    try:
        st.info("⏳ Memulai proses scraping...")
        
        # Create containers for progress and status
        progress_container = st.container()
        status_container = st.container()
        
        with progress_container:
            progress_bar = st.progress(0)
        
        # Initialize scraper
        scraper = InstagramScraper(strategy=SCRAPER_STRATEGY)
        
        # Scrape each URL individually for granular progress
        raw_records = []
        for idx, url in enumerate(parsed_urls):
            with status_container:
                st.status(f"Scraping: {url}", state="running")
            
            # Scrape single URL
            record = scraper._scrape_one(url)
            raw_records.append(record)
            
            # Update progress bar
            progress = (idx + 1) / len(parsed_urls)
            progress_bar.progress(progress)
        
        # Process records
        processed = [process_record(r) for r in raw_records]
        
        # Validate records
        valid_records = []
        invalid_records = []
        for record in processed:
            ok, reason = validate_record(record)
            if ok:
                valid_records.append(record)
            else:
                invalid_records.append({"url": record.get("url"), "reason": reason})
        
        # Upload to Google Sheets
        service = SpreadsheetService()
        service.ensure_header()
        appended = service.append_rows(valid_records)
        
        # Store results in session state
        st.session_state["results"] = valid_records
        st.session_state["invalid"] = invalid_records
        st.session_state["appended_count"] = appended
        st.session_state["has_results"] = True
        
        # Success message
        st.success(f"✅ Scraping selesai! {len(valid_records)} data berhasil diproses.")
        
    except ImportError as e:
        st.error("❌ Modul scraper tidak ditemukan. Pastikan semua file project ada.")
        st.exception(e)
    except Exception as e:
        st.error(f"❌ Error: {str(e)}")
        st.exception(e)

# ============================================================================
# SECTION 3: RESULTS TABLE (shown only if has results)
# ============================================================================

if st.session_state["has_results"] and len(st.session_state["results"]) > 0:
    st.divider()
    st.header("📊 Hasil Engagement")
    
    results = st.session_state["results"]
    metrics = calculate_metrics(results)
    
    # Show metrics in 5 columns
    metric_cols = st.columns(5)
    
    with metric_cols[0]:
        st.metric("Total URL Diproses", metrics["total_urls"])
    
    with metric_cols[1]:
        st.metric("Total Likes", f"{metrics['total_likes']:,}")
    
    with metric_cols[2]:
        st.metric("Total Comments", f"{metrics['total_comments']:,}")
    
    with metric_cols[3]:
        st.metric("Total Views", f"{metrics['total_views']:,}")
    
    with metric_cols[4]:
        st.metric("Baris Baru di Sheets", st.session_state["appended_count"])
    
    # Display results table
    df = pd.DataFrame(results)
    
    # Reorder columns as specified
    column_order = [
        "url", "content_type", "post_date", "likes", "comments", "views",
        "reposts", "saves", "shares", "caption", "ingestion_timestamp"
    ]
    available_columns = [col for col in column_order if col in df.columns]
    df = df[available_columns]
    
    # Display dataframe with column config
    st.dataframe(
        df,
        use_container_width=True,
        height=400,
        column_config={
            "url": st.column_config.LinkColumn("URL", display_text="🔗 Buka"),
            "likes": st.column_config.NumberColumn("Likes", format="%d"),
            "comments": st.column_config.NumberColumn("Comments", format="%d"),
            "views": st.column_config.NumberColumn("Views", format="%d"),
            "content_type": st.column_config.TextColumn("Tipe Konten"),
            "post_date": st.column_config.TextColumn("Tanggal Post"),
            "ingestion_timestamp": st.column_config.TextColumn("Waktu Scraping"),
        }
    )
    
    # ========================================================================
    # SECTION 4: ACTION BUTTONS (CSV Download & Google Sheets Link)
    # ========================================================================
    
    st.divider()
    col1, col2 = st.columns(2)
    
    with col1:
        # Download CSV button
        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="⬇️ Download Hasil (CSV)",
            data=csv,
            file_name="engagement_report.csv",
            mime="text/csv",
            use_container_width=True
        )
    
    with col2:
        # Open Google Sheets button
        if GOOGLE_SHEET_ID.startswith("https://"):
            sheets_url = GOOGLE_SHEET_ID
        else:
            sheets_url = f"https://docs.google.com/spreadsheets/d/{GOOGLE_SHEET_ID}"
        
        st.link_button(
            "📄 Lihat Google Sheets",
            url=sheets_url,
            use_container_width=True
        )
    
    # ========================================================================
    # SECTION 5: INVALID RECORDS (shown if any failed)
    # ========================================================================
    
    if st.session_state["invalid"] and len(st.session_state["invalid"]) > 0:
        st.divider()
        with st.expander(f"⚠️ URL yang gagal diproses ({len(st.session_state['invalid'])} URL)"):
            invalid_df = pd.DataFrame(st.session_state["invalid"])
            st.dataframe(invalid_df, use_container_width=True)

# ============================================================================
# SECTION 6: FOOTER
# ============================================================================

st.divider()
st.markdown(
    "<p style='text-align: center; color: gray; font-size: 0.9em;'>"
    "Instagram Engagement Scraper • Built with Streamlit"
    "</p>",
    unsafe_allow_html=True
)
