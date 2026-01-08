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
from ranker import rank_jobs, rank_jobs_with_scores, get_daily_job_limit
from resume_manager import resume_manager


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
            # Rank and select top jobs (with fit scores if resume is loaded)
            max_jobs = get_daily_job_limit()

            if resume_manager.has_resume():
                print(f"\nUsing resume for fit scoring...")
                print(resume_manager.get_resume_summary())
                top_scored_jobs = rank_jobs_with_scores(new_jobs, max_results=max_jobs)
                print(f"\nSelected top {len(top_scored_jobs)} jobs to send (with fit scores)")

                # Send notifications with fit scores
                time_of_day = "Morning" if datetime.now().hour < 12 else "Evening"
                sent = await notifier.send_job_batch(
                    top_scored_jobs,
                    batch_title=f"{time_of_day} Search - {datetime.now().strftime('%b %d')}"
                )

                # Extract jobs for database marking
                top_jobs = [sj.job for sj in top_scored_jobs]
            else:
                top_jobs = rank_jobs(new_jobs, max_results=max_jobs)
                print(f"\nSelected top {len(top_jobs)} jobs to send")

                # Send notifications (without fit scores)
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

    # Add resume status
    if resume_manager.has_resume():
        message += f"\n*Resume:* Loaded ✓\n"
        message += f"_{resume_manager.get_resume_summary()}_\n"
    else:
        message += "\n*Resume:* Not loaded\n"
        message += "_Use --resume to upload for fit scoring_\n"

    message += f"\n_Last check: {datetime.now().strftime('%Y-%m-%d %H:%M')}_"

    await notifier.send_message(message)
    print("Status sent to Telegram")


def upload_resume(file_path: str):
    """Upload and parse a resume file."""
    print(f"Loading resume from: {file_path}")
    try:
        resume = resume_manager.update_resume_from_file(file_path)
        print("\nResume loaded successfully!")
        print(f"  Skills found: {len(resume.skills)}")
        print(f"  Job titles: {resume.job_titles}")
        print(f"  Experience: {resume.experience_years}+ years")
        print(f"  Certifications: {resume.certifications}")
        print(f"  Keywords extracted: {len(resume.keywords)}")
        print(f"\nResume saved. Jobs will now be scored based on fit.")
    except FileNotFoundError:
        print(f"Error: File not found: {file_path}")
    except ImportError as e:
        print(f"Error: {e}")
    except Exception as e:
        print(f"Error loading resume: {e}")


def upload_resume_text(text: str):
    """Upload resume from text input."""
    print("Processing resume text...")
    resume = resume_manager.update_resume(text)
    print("\nResume loaded successfully!")
    print(f"  Skills found: {len(resume.skills)}")
    print(f"  Experience: {resume.experience_years}+ years")
    print(f"  Certifications: {resume.certifications}")
    print(f"\nResume saved. Jobs will now be scored based on fit.")


def set_current_job(title: str, description: str = ""):
    """Set current job for comparison."""
    resume_manager.update_current_job(title, description)
    print(f"Current job set: {title}")
    print("Jobs will be scored against this for career progression.")


def show_resume_info():
    """Show current resume status."""
    if resume_manager.has_resume():
        resume = resume_manager.resume
        print("\n=== Resume Information ===")
        print(f"Last updated: {resume.last_updated[:10] if resume.last_updated else 'Unknown'}")
        print(f"\nSkills ({len(resume.skills)}):")
        for skill in resume.skills[:10]:
            print(f"  • {skill}")
        if len(resume.skills) > 10:
            print(f"  ... and {len(resume.skills) - 10} more")

        print(f"\nJob Titles: {', '.join(resume.job_titles) if resume.job_titles else 'None extracted'}")
        print(f"Experience: {resume.experience_years}+ years")
        print(f"Certifications: {', '.join(resume.certifications) if resume.certifications else 'None found'}")
        print(f"Keywords: {len(resume.keywords)} unique terms")

        if resume_manager.current_job:
            print(f"\nCurrent Job: {resume_manager.current_job.title}")
    else:
        print("\nNo resume loaded.")
        print("Use --resume <file> to upload your resume for fit scoring.")


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Job Scout Agent - Find and match jobs based on your resume",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python agent.py                     # Run job scout
  python agent.py --resume myresume.pdf   # Upload resume for fit scoring
  python agent.py --resume-info       # Show current resume status
  python agent.py --current-job "IT Support Specialist"  # Set current job
  python agent.py --status            # Send status to Telegram
        """
    )

    # Job scout options
    parser.add_argument("--welcome", action="store_true", help="Send welcome message")
    parser.add_argument("--force", action="store_true", help="Force notify even if no new jobs")
    parser.add_argument("--status", action="store_true", help="Send status to Telegram")
    parser.add_argument("--test", action="store_true", help="Test Telegram connection")

    # Resume options
    parser.add_argument("--resume", metavar="FILE",
                       help="Upload resume from file (PDF or TXT) for fit scoring")
    parser.add_argument("--resume-text", metavar="TEXT",
                       help="Upload resume from text string")
    parser.add_argument("--resume-info", action="store_true",
                       help="Show current resume information")
    parser.add_argument("--current-job", metavar="TITLE",
                       help="Set your current job title for career progression scoring")
    parser.add_argument("--job-description", metavar="DESC", default="",
                       help="Optional: description of current job (use with --current-job)")

    args = parser.parse_args()

    # Handle resume commands first
    if args.resume:
        upload_resume(args.resume)
        return

    if args.resume_text:
        upload_resume_text(args.resume_text)
        return

    if args.resume_info:
        show_resume_info()
        return

    if args.current_job:
        set_current_job(args.current_job, args.job_description)
        return

    # Handle other commands
    if args.test:
        from telegram_notifier import test_telegram
        asyncio.run(test_telegram())
    elif args.status:
        asyncio.run(send_status())
    else:
        asyncio.run(run_job_scout(send_welcome=args.welcome, force_notify=args.force))


if __name__ == "__main__":
    main()
