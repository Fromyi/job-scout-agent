"""Job Scout Agent Configuration."""
import os
from dataclasses import dataclass, field
from typing import List

@dataclass
class JobPreferences:
    """User job search preferences."""

    # Target roles
    roles: List[str] = field(default_factory=lambda: [
        "IT Support",
        "IT Support Specialist",
        "IT Help Desk",
        "Help Desk Technician",
        "Customer Experience Lead",
        "Customer Support Lead",
        "Technical Support Lead",
        "AI Integration Support",
        "AI Support Specialist",
        "Technical Support Engineer",
        "IT Support Analyst",
        "Desktop Support",
        "Service Desk Analyst",
        "Systems Support",
    ])

    # Location - Bayonne, NJ with 5-30 mile radius preference
    location: str = "Bayonne, NJ"
    location_radius_min: int = 5   # miles (minimum)
    location_radius_max: int = 30  # miles (maximum)
    remote_ok: bool = True  # Include remote jobs
    hybrid_ok: bool = True  # Include hybrid jobs

    # NYC restrictions - only Manhattan and Brooklyn allowed
    nyc_allowed_boroughs: list = None  # Set in __post_init__

    # Areas within target range
    valid_locations: list = None  # Set in __post_init__

    def __post_init__(self):
        # NYC - ONLY Manhattan and Brooklyn allowed
        self.nyc_allowed_boroughs = ["manhattan", "brooklyn"]

        # NJ - ONLY 5-30 mile radius (close + medium)
        self.valid_locations = [
            # NJ Cities - Close (5-15 miles from Bayonne)
            "bayonne", "jersey city", "hoboken", "newark", "secaucus",
            "kearny", "harrison", "union city", "west new york", "north bergen",
            # NJ Cities - Medium (15-30 miles)
            "elizabeth", "fort lee", "hackensack", "englewood", "paramus",
            "clifton", "passaic", "paterson", "east orange", "orange",
            "irvington", "bloomfield", "montclair", "linden", "rahway",
            "cranford", "woodbridge", "edison",
            # NYC - Only Manhattan and Brooklyn
            "manhattan", "brooklyn",
            # Generic
            "remote", "hybrid", "new jersey", "nj",
        ]

        # Excluded locations (>30 mi from Bayonne)
        self.excluded_locations = [
            "morristown", "parsippany", "wayne", "new brunswick", "perth amboy",
            "trenton", "princeton", "somerset", "toms river",
            "queens", "bronx", "staten island",
        ]

    # Experience level
    experience_levels: List[str] = field(default_factory=lambda: [
        "entry_level",
        "mid_level",
        "associate",
    ])

    # Salary
    min_salary: int = 70000

    # Job age (only show jobs posted within X days)
    max_days_old: int = 7


@dataclass
class TelegramConfig:
    """Telegram bot configuration."""
    bot_token: str = "8139270854:AAFBIu_fbg6odREDZ8KEVsna1fL1TqQzlCY"
    chat_id: int = 843945987


@dataclass
class ScraperConfig:
    """Scraper settings."""
    sources: List[str] = field(default_factory=lambda: ["linkedin", "indeed"])
    max_results_per_source: int = 25
    request_delay: float = 2.0  # Seconds between requests


@dataclass
class Config:
    """Main configuration."""
    preferences: JobPreferences = field(default_factory=JobPreferences)
    telegram: TelegramConfig = field(default_factory=TelegramConfig)
    scraper: ScraperConfig = field(default_factory=ScraperConfig)

    # Database for tracking seen jobs
    db_path: str = "jobs.db"

    # Schedule (for reference - actual cron handles this)
    morning_hour: int = 8
    evening_hour: int = 18


# Global config instance
config = Config()
