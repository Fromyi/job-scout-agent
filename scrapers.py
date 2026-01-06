"""Job scrapers for LinkedIn and Indeed."""
import asyncio
import re
import hashlib
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import List, Optional
from urllib.parse import quote_plus

import httpx
from bs4 import BeautifulSoup

from config import config


@dataclass
class Job:
    """Job posting data."""
    id: str
    title: str
    company: str
    location: str
    salary: Optional[str]
    url: str
    source: str
    posted_date: Optional[str] = None
    description_snippet: Optional[str] = None

    def to_telegram_message(self) -> str:
        """Format job for Telegram."""
        salary_text = f"\n💰 {self.salary}" if self.salary else ""
        return (
            f"🔹 *{self.title}*\n"
            f"🏢 {self.company}\n"
            f"📍 {self.location}{salary_text}\n"
            f"🔗 [Apply]({self.url})\n"
            f"📅 {self.posted_date or 'Recent'} • {self.source.title()}"
        )


class LinkedInScraper:
    """Scrape jobs from LinkedIn."""

    BASE_URL = "https://www.linkedin.com/jobs/search"

    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        }

    async def search(self, query: str, location: str) -> List[Job]:
        """Search LinkedIn for jobs."""
        jobs = []

        # Build URL
        params = {
            "keywords": query,
            "location": location,
            "f_TPR": "r604800",  # Past week
            "f_WT": "2",  # Remote
            "sortBy": "DD",  # Most recent
        }

        url = f"{self.BASE_URL}?keywords={quote_plus(query)}&location={quote_plus(location)}&f_TPR=r604800&sortBy=DD"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=self.headers)

                if response.status_code != 200:
                    print(f"LinkedIn returned {response.status_code}")
                    return jobs

                soup = BeautifulSoup(response.text, "html.parser")

                # Find job cards
                job_cards = soup.find_all("div", class_="base-card")[:config.scraper.max_results_per_source]

                for card in job_cards:
                    try:
                        title_elem = card.find("h3", class_="base-search-card__title")
                        company_elem = card.find("h4", class_="base-search-card__subtitle")
                        location_elem = card.find("span", class_="job-search-card__location")
                        link_elem = card.find("a", class_="base-card__full-link")
                        time_elem = card.find("time")

                        if not all([title_elem, company_elem, link_elem]):
                            continue

                        job_url = link_elem.get("href", "").split("?")[0]
                        job_id = hashlib.md5(job_url.encode()).hexdigest()[:12]

                        jobs.append(Job(
                            id=f"li_{job_id}",
                            title=title_elem.get_text(strip=True),
                            company=company_elem.get_text(strip=True),
                            location=location_elem.get_text(strip=True) if location_elem else location,
                            salary=None,  # LinkedIn doesn't always show salary
                            url=job_url,
                            source="linkedin",
                            posted_date=time_elem.get("datetime", "")[:10] if time_elem else None,
                        ))
                    except Exception as e:
                        continue

        except Exception as e:
            print(f"LinkedIn scraper error: {e}")

        return jobs


class IndeedScraper:
    """Scrape jobs from Indeed."""

    BASE_URL = "https://www.indeed.com/jobs"

    def __init__(self):
        # More realistic browser headers to avoid 403
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Cache-Control": "max-age=0",
            "sec-ch-ua": '"Not A(Brand";v="99", "Google Chrome";v="121", "Chromium";v="121"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"macOS"',
        }

    async def search(self, query: str, location: str) -> List[Job]:
        """Search Indeed for jobs."""
        jobs = []

        url = f"{self.BASE_URL}?q={quote_plus(query)}&l={quote_plus(location)}&fromage=7&sort=date"

        try:
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                response = await client.get(url, headers=self.headers)

                if response.status_code != 200:
                    print(f"Indeed returned {response.status_code}")
                    return jobs

                soup = BeautifulSoup(response.text, "html.parser")

                # Find job cards - Indeed uses various class patterns
                job_cards = soup.find_all("div", class_=re.compile("job_seen_beacon|jobsearch-ResultsList"))

                # Try alternative selectors
                if not job_cards:
                    job_cards = soup.find_all("td", class_="resultContent")

                if not job_cards:
                    job_cards = soup.select("[data-jk]")[:config.scraper.max_results_per_source]

                for card in job_cards[:config.scraper.max_results_per_source]:
                    try:
                        # Multiple selector attempts for Indeed's varying HTML
                        title_elem = (
                            card.find("h2", class_=re.compile("jobTitle")) or
                            card.find("a", class_=re.compile("jcs-JobTitle")) or
                            card.find("span", {"title": True})
                        )

                        company_elem = (
                            card.find("span", class_=re.compile("companyName|company")) or
                            card.find("span", {"data-testid": "company-name"})
                        )

                        location_elem = (
                            card.find("div", class_=re.compile("companyLocation")) or
                            card.find("span", class_=re.compile("location"))
                        )

                        salary_elem = (
                            card.find("div", class_=re.compile("salary-snippet")) or
                            card.find("span", class_=re.compile("salary"))
                        )

                        # Get job URL
                        link_elem = card.find("a", href=True)
                        job_key = card.get("data-jk") or (link_elem.get("data-jk") if link_elem else None)

                        if not title_elem:
                            continue

                        title = title_elem.get_text(strip=True)
                        company = company_elem.get_text(strip=True) if company_elem else "Unknown"
                        loc = location_elem.get_text(strip=True) if location_elem else location
                        salary = salary_elem.get_text(strip=True) if salary_elem else None

                        if job_key:
                            job_url = f"https://www.indeed.com/viewjob?jk={job_key}"
                            job_id = job_key
                        elif link_elem:
                            href = link_elem.get("href", "")
                            job_url = f"https://www.indeed.com{href}" if href.startswith("/") else href
                            job_id = hashlib.md5(job_url.encode()).hexdigest()[:12]
                        else:
                            continue

                        jobs.append(Job(
                            id=f"in_{job_id}",
                            title=title,
                            company=company,
                            location=loc,
                            salary=salary,
                            url=job_url,
                            source="indeed",
                        ))
                    except Exception as e:
                        continue

        except Exception as e:
            print(f"Indeed scraper error: {e}")

        return jobs


class GlassdoorScraper:
    """Scrape jobs from Glassdoor."""

    BASE_URL = "https://www.glassdoor.com/Job/jobs.htm"

    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }

    async def search(self, query: str, location: str) -> List[Job]:
        """Search Glassdoor for jobs."""
        jobs = []
        url = f"{self.BASE_URL}?sc.keyword={quote_plus(query)}&locT=C&locKeyword={quote_plus(location)}&fromAge=7"

        try:
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                response = await client.get(url, headers=self.headers)

                if response.status_code != 200:
                    return jobs

                soup = BeautifulSoup(response.text, "html.parser")
                job_cards = soup.find_all("li", class_=re.compile("JobsList_jobListItem"))[:config.scraper.max_results_per_source]

                for card in job_cards:
                    try:
                        title_elem = card.find("a", class_=re.compile("JobCard_jobTitle"))
                        company_elem = card.find("span", class_=re.compile("EmployerProfile_companyName"))
                        location_elem = card.find("div", class_=re.compile("JobCard_location"))

                        if not title_elem:
                            continue

                        job_url = title_elem.get("href", "")
                        if job_url and not job_url.startswith("http"):
                            job_url = f"https://www.glassdoor.com{job_url}"

                        job_id = hashlib.md5(job_url.encode()).hexdigest()[:12]

                        jobs.append(Job(
                            id=f"gd_{job_id}",
                            title=title_elem.get_text(strip=True),
                            company=company_elem.get_text(strip=True) if company_elem else "Unknown",
                            location=location_elem.get_text(strip=True) if location_elem else location,
                            salary=None,
                            url=job_url,
                            source="glassdoor",
                        ))
                    except:
                        continue

        except Exception as e:
            print(f"Glassdoor error: {e}")

        return jobs


async def scrape_all_jobs() -> List[Job]:
    """Scrape jobs from all configured sources."""
    all_jobs = []

    linkedin = LinkedInScraper()
    indeed = IndeedScraper()
    glassdoor = GlassdoorScraper()

    # Search each role
    for role in config.preferences.roles:
        print(f"Searching for: {role}")

        # Add delay between searches
        await asyncio.sleep(config.scraper.request_delay)

        if "linkedin" in config.scraper.sources:
            jobs = await linkedin.search(role, config.preferences.location)
            all_jobs.extend(jobs)
            print(f"  LinkedIn: {len(jobs)} jobs")

        await asyncio.sleep(config.scraper.request_delay)

        if "indeed" in config.scraper.sources:
            jobs = await indeed.search(role, config.preferences.location)
            all_jobs.extend(jobs)
            if jobs:
                print(f"  Indeed: {len(jobs)} jobs")

        await asyncio.sleep(config.scraper.request_delay)

        # Always try Glassdoor as backup
        jobs = await glassdoor.search(role, config.preferences.location)
        all_jobs.extend(jobs)
        if jobs:
            print(f"  Glassdoor: {len(jobs)} jobs")

    # Deduplicate by job ID
    seen_ids = set()
    unique_jobs = []
    for job in all_jobs:
        if job.id not in seen_ids:
            seen_ids.add(job.id)
            unique_jobs.append(job)

    print(f"\nTotal unique jobs found: {len(unique_jobs)}")
    return unique_jobs


if __name__ == "__main__":
    # Test scrapers
    jobs = asyncio.run(scrape_all_jobs())
    for job in jobs[:5]:
        print(f"\n{job.title} at {job.company}")
        print(f"  {job.location} - {job.source}")
        print(f"  {job.url}")
