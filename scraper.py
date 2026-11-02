import logging
import hashlib
import re
from typing import List, Dict, Any
import requests
from bs4 import BeautifulSoup
from config import DEFAULT_PLATFORMS

logger = logging.getLogger(__name__)

def make_job_id(site: str, title: str, company: str, url: str) -> str:
    """Generates a stable unique hash identifier for deduplication"""
    raw = f"{site.lower()}:{company.lower()}:{title.lower()}:{url}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()

def scrape_with_jobspy(search_term: str, location: str = "Philippines", results_wanted: int = 10) -> List[Dict[str, Any]]:
    """Primary scraper using python-jobspy for LinkedIn and Indeed"""
    job_results = []
    try:
        from jobspy import scrape_jobs
        
        # Determine indeed country
        country_indeed = 'philippines' if 'philippines' in location.lower() or 'makati' in location.lower() or 'manila' in location.lower() else 'usa'
        
        df = scrape_jobs(
            site_name=DEFAULT_PLATFORMS,
            search_term=search_term,
            location=location,
            results_wanted=results_wanted,
            hours_old=72,
            country_indeed=country_indeed
        )
        
        if df is not None and not df.empty:
            for _, row in df.iterrows():
                site = str(row.get("site", "linkedin"))
                title = str(row.get("title", ""))
                company = str(row.get("company", "Company"))
                job_url = str(row.get("job_url", ""))
                job_id = make_job_id(site, title, company, job_url)
                
                job_results.append({
                    "id": job_id,
                    "site": site,
                    "title": title,
                    "company": company,
                    "location": str(row.get("location", location)),
                    "date_posted": str(row.get("date_posted", "Recent")),
                    "job_url": job_url,
                    "description": str(row.get("description", ""))
                })
    except Exception as e:
        logger.warning(f"JobSpy scrape error for '{search_term}': {e}. Falling back to LinkedIn Guest API.")
        
    return job_results

def scrape_linkedin_guest_fallback(search_term: str, location: str = "Philippines", results_wanted: int = 10) -> List[Dict[str, Any]]:
    """Fallback scraper utilizing LinkedIn public guest job search endpoint"""
    job_results = []
    try:
        url = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9"
        }
        params = {
            "keywords": search_term,
            "location": location,
            "start": 0
        }
        resp = requests.get(url, params=params, headers=headers, timeout=10)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            cards = soup.find_all("li")
            for card in cards[:results_wanted]:
                title_elem = card.find("h3", class_="base-search-card__title")
                company_elem = card.find("h4", class_="base-search-card__subtitle")
                location_elem = card.find("span", class_="job-search-card__location")
                link_elem = card.find("a", class_="base-card__full-link")
                time_elem = card.find("time")
                
                if title_elem and link_elem:
                    title = title_elem.get_text(strip=True)
                    company = company_elem.get_text(strip=True) if company_elem else "Company"
                    job_loc = location_elem.get_text(strip=True) if location_elem else location
                    job_url = link_elem.get("href", "").split("?")[0] # Clean tracking params
                    date_posted = time_elem.get_text(strip=True) if time_elem else "Recent"
                    job_id = make_job_id("linkedin", title, company, job_url)
                    
                    job_results.append({
                        "id": job_id,
                        "site": "linkedin",
                        "title": title,
                        "company": company,
                        "location": job_loc,
                        "date_posted": date_posted,
                        "job_url": job_url,
                        "description": f"{title} at {company} in {job_loc}."
                    })
    except Exception as e:
        logger.error(f"Fallback LinkedIn scraper error: {e}")
        
    return job_results

def fetch_jobs(search_term: str, location: str = "Philippines", results_wanted: int = 8) -> List[Dict[str, Any]]:
    """Master search function that combines Indeed and LinkedIn jobs robustly"""
    jobs = scrape_with_jobspy(search_term, location, results_wanted)
    
    # Check if LinkedIn was blocked or returned no results
    has_linkedin = any(j.get("site", "").lower() == "linkedin" for j in jobs)
    if not has_linkedin:
        linkedin_fallback = scrape_linkedin_guest_fallback(search_term, location, results_wanted=results_wanted)
        jobs.extend(linkedin_fallback)
        
    return jobs
