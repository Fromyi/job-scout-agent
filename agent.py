#!/usr/bin/env python3
"""
Job Scout Agent - Main entry point.
Scrapes job postings and sends alerts via Telegram.
"""
import asyncio
import argparse
from datetime import datetime

from config import config
from scrapers import scrape_all_jobs
from database import JobDatabase
from telegram_notifier import TelegramNotifier
from ranker import rank_jobs, get_daily_job_limit


async def run_job_scout(send_welcome: bool = False, force_notify: bool = False):
    """Main job scout routine."""
    print(f"\n{'='*50}")
    print(f"Job Scout Agent - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*50}\n")

    db = JobDatabase()
    notifier = TelegramNotifier()

    # Send welcome message on first run
    if send_welcome:
        print("Sending welcome message...")
        await notifier.send_welcome_message()
        await asyncio.sleep(1)

    try:
        # Scrape all job sources
        print("Scraping job boards...")
        all_jobs = await scrape_all_jobs()

        if not all_jobs:
            print("No jobs found from scrapers")
            if force_notify:
                await notifier.send_no_jobs_message()
            return

        # Filter to only new jobs
        new_jobs = db.filter_new_jobs(all_jobs)
        print(f"\nNew jobs (not seen before): {len(new_jobs)}")

        if new_jobs:
            # Rank and select top jobs
            max_jobs = get_daily_job_limit()
            top_jobs = rank_jobs(new_jobs, max_results=max_jobs)
            print(f"\nSelected top {len(top_jobs)} jobs to send")

            # Send notifications for top jobs only
            time_of_day = "Morning" if datetime.now().hour < 12 else "Evening"
            sent = await notifier.send_job_batch(
                top_jobs,
                batch_title=f"{time_of_day} Search - {datetime.now().strftime('%b %d')}"
            )
            print(f"Sent {sent} job alerts via Telegram")

            # Mark top jobs as notified
            db.mark_jobs_seen(top_jobs, notified=True)
        else:
            print("No new jobs to notify about")
            if force_notify:
                await notifier.send_no_jobs_message()

        # Mark all scraped jobs as seen (even if not notified)
        db.mark_jobs_seen(all_jobs, notified=False)

        # Print stats
        stats = db.get_stats()
        print(f"\nDatabase stats:")
        print(f"  Total jobs seen: {stats['total_seen']}")
        print(f"  Found today: {stats['found_today']}")
        print(f"  By source: {stats['by_source']}")

        # Cleanup old entries
        db.cleanup_old_jobs(days=30)

    except Exception as e:
        print(f"Error during job scout: {e}")
        await notifier.send_error_message(str(e))
        raise


async def send_status():
    """Send status update to Telegram."""
    db = JobDatabase()
    notifier = TelegramNotifier()
    stats = db.get_stats()

    message = (
        "📊 *Job Scout Status*\n\n"
        f"🔍 Total jobs tracked: {stats['total_seen']}\n"
        f"📬 Jobs notified: {stats['total_notified']}\n"
        f"📅 Found today: {stats['found_today']}\n\n"
        "*By Source:*\n"
    )
    for source, count in stats.get('by_source', {}).items():
        message += f"  • {source.title()}: {count}\n"

    message += f"\n_Last check: {datetime.now().strftime('%Y-%m-%d %H:%M')}_"

    await notifier.send_message(message)
    print("Status sent to Telegram")


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Job Scout Agent")
    parser.add_argument("--welcome", action="store_true", help="Send welcome message")
    parser.add_argument("--force", action="store_true", help="Force notify even if no new jobs")
    parser.add_argument("--status", action="store_true", help="Send status to Telegram")
    parser.add_argument("--test", action="store_true", help="Test Telegram connection")

    args = parser.parse_args()

    if args.test:
        from telegram_notifier import test_telegram
        asyncio.run(test_telegram())
    elif args.status:
        asyncio.run(send_status())
    else:
        asyncio.run(run_job_scout(send_welcome=args.welcome, force_notify=args.force))


if __name__ == "__main__":
    main()
