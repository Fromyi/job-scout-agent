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

    # Location - Bayonne, NJ with 30 mile radius
    location: str = "Bayonne, NJ"
    location_radius: int = 30  # miles
    remote_ok: bool = True  # Include remote jobs
    hybrid_ok: bool = True  # Include hybrid jobs

    # Areas within 30 miles of Bayonne, NJ
    valid_locations: list = None  # Set in __post_init__

    def __post_init__(self):
        self.valid_locations = [
            # NJ Cities (within 30 miles of Bayonne)
            "bayonne", "jersey city", "hoboken", "newark", "elizabeth",
            "union city", "west new york", "north bergen", "secaucus",
            "kearny", "harrison", "east orange", "orange", "irvington",
            "bloomfield", "montclair", "clifton", "passaic", "paterson",
            "hackensack", "fort lee", "englewood", "paramus", "wayne",
            "morristown", "parsippany", "edison", "new brunswick",
            "woodbridge", "perth amboy", "linden", "rahway", "cranford",
            # NYC (all boroughs accessible)
            "new york", "nyc", "manhattan", "brooklyn", "queens",
            "bronx", "staten island",
            # Generic
            "remote", "hybrid", "new jersey", "nj",
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
