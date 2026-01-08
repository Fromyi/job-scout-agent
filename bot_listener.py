#!/usr/bin/env python3
"""
Telegram Bot Listener - Listens for commands and responds.
Run this as a background service to enable /search, /status, /more commands.
"""
import asyncio
import json
from datetime import datetime
from typing import Optional
import httpx

from config import config
from telegram_notifier import TelegramNotifier
from database import JobDatabase
from scrapers import scrape_all_jobs
from ranker import rank_jobs, rank_jobs_with_scores, get_daily_job_limit
from resume_manager import resume_manager


class TelegramBotListener:
    """Listen for Telegram commands and respond."""

    def __init__(self):
        self.bot_token = config.telegram.bot_token
        self.chat_id = config.telegram.chat_id
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"
        self.notifier = TelegramNotifier()
        self.last_update_id = 0
        self.is_paused = False

    async def get_updates(self, timeout: int = 30) -> list:
        """Get new messages from Telegram using long polling."""
        url = f"{self.base_url}/getUpdates"
        params = {
            "offset": self.last_update_id + 1,
            "timeout": timeout,
            "allowed_updates": ["message"],
        }

        try:
            async with httpx.AsyncClient(timeout=timeout + 10) as client:
                response = await client.get(url, params=params)

                if response.status_code != 200:
                    print(f"getUpdates error: {response.status_code}")
                    return []

                data = response.json()

                if not data.get("ok"):
                    return []

                updates = data.get("result", [])

                if updates:
                    self.last_update_id = updates[-1]["update_id"]

                return updates

        except httpx.TimeoutException:
            return []  # Normal for long polling
        except Exception as e:
            print(f"Error getting updates: {e}")
            return []

    async def handle_command(self, command: str, chat_id: int, message_id: int):
        """Handle a bot command."""
        # Only respond to our configured chat
        if chat_id != self.chat_id:
            print(f"Ignoring message from unknown chat: {chat_id}")
            return

        command = command.lower().strip()
        print(f"Received command: {command}")

        if command == "/start" or command == "/help":
            await self.cmd_help()

        elif command == "/status":
            await self.cmd_status()

        elif command == "/search":
            await self.cmd_search()

        elif command.startswith("/more"):
            # Parse optional count: /more or /more 15
            parts = command.split()
            count = 10
            if len(parts) > 1:
                try:
                    count = int(parts[1])
                    count = min(max(count, 1), 25)  # Limit 1-25
                except:
                    pass
            await self.cmd_more(count)

        elif command == "/stop" or command == "/pause":
            await self.cmd_stop()

        elif command == "/resume" or command == "/start_alerts":
            await self.cmd_resume()

        elif command == "/quick":
            await self.cmd_quick()

        else:
            # Unknown command
            await self.notifier.send_message(
                f"Unknown command: {command}\n\n"
                "Available commands:\n"
                "/search - Run job search now\n"
                "/more - Get 10 more jobs\n"
                "/more 20 - Get 20 more jobs\n"
                "/status - Check bot status\n"
                "/stop - Pause alerts\n"
                "/resume - Resume alerts"
            )

    async def cmd_help(self):
        """Send help message."""
        message = (
            "🤖 *Job Scout Bot Commands*\n\n"
            "/search - Run a new job search\n"
            "/more - Get 10 more job matches\n"
            "/more 15 - Get 15 more jobs\n"
            "/status - Check bot status\n"
            "/stop - Pause job alerts\n"
            "/resume - Resume job alerts\n"
            "/help - Show this message\n\n"
            "_Jobs are automatically sent at 8 AM & 6 PM_"
        )
        await self.notifier.send_message(message)

    async def cmd_status(self):
        """Send status update."""
        db = JobDatabase()
        stats = db.get_stats()

        status = "🟢 Active" if not self.is_paused else "⏸️ Paused"

        message = (
            "📊 *Job Scout Status*\n\n"
            f"🔄 Bot Status: {status}\n"
            f"🔍 Total jobs tracked: {stats['total_seen']}\n"
            f"📬 Jobs notified: {stats['total_notified']}\n"
            f"📅 Found today: {stats['found_today']}\n\n"
            "*By Source:*\n"
        )
        for source, count in stats.get('by_source', {}).items():
            message += f"  • {source.title()}: {count}\n"

        # Resume status
        if resume_manager.has_resume():
            message += f"\n*Resume:* Loaded ✅\n"
            message += f"_{resume_manager.get_resume_summary()}_\n"
        else:
            message += "\n*Resume:* Not loaded\n"

        message += f"\n_Last check: {datetime.now().strftime('%Y-%m-%d %H:%M')}_"

        await self.notifier.send_message(message)

    async def cmd_search(self):
        """Run a new job search."""
        if self.is_paused:
            await self.notifier.send_message(
                "⏸️ Bot is paused. Use /resume to enable alerts first."
            )
            return

        await self.notifier.send_message("🔍 Starting job search...")

        try:
            db = JobDatabase()

            # Scrape all job sources
            all_jobs = await scrape_all_jobs()

            if not all_jobs:
                await self.notifier.send_message(
                    "😕 No jobs found from job boards. Try again later."
                )
                return

            # Filter to only new jobs
            new_jobs = db.filter_new_jobs(all_jobs)

            if not new_jobs:
                await self.notifier.send_message(
                    "✅ No *new* jobs found since last search.\n"
                    f"Total scraped: {len(all_jobs)}\n\n"
                    "_Use /more to see previously found jobs._"
                )
                db.mark_jobs_seen(all_jobs, notified=False)
                return

            # Rank and send
            max_jobs = get_daily_job_limit()

            if resume_manager.has_resume():
                top_jobs = rank_jobs_with_scores(new_jobs, max_results=max_jobs)
                await self.notifier.send_job_batch(
                    top_jobs,
                    batch_title=f"Search Results - {datetime.now().strftime('%I:%M %p')}"
                )
                db.mark_jobs_seen([sj.job for sj in top_jobs], notified=True)
            else:
                top_jobs = rank_jobs(new_jobs, max_results=max_jobs)
                await self.notifier.send_job_batch(
                    top_jobs,
                    batch_title=f"Search Results - {datetime.now().strftime('%I:%M %p')}"
                )
                db.mark_jobs_seen(top_jobs, notified=True)

            db.mark_jobs_seen(all_jobs, notified=False)

        except Exception as e:
            await self.notifier.send_message(f"❌ Search error: {e}")

    async def cmd_more(self, count: int = 10):
        """Send more job matches."""
        if self.is_paused:
            await self.notifier.send_message(
                "⏸️ Bot is paused. Use /resume to enable alerts first."
            )
            return

        await self.notifier.send_message(f"🔍 Fetching {count} more jobs...")

        try:
            db = JobDatabase()

            # Scrape fresh jobs
            all_jobs = await scrape_all_jobs()

            if not all_jobs:
                await self.notifier.send_message(
                    "😕 No jobs found from job boards. Try again later."
                )
                return

            # Rank all jobs (including previously seen)
            if resume_manager.has_resume():
                top_jobs = rank_jobs_with_scores(all_jobs, max_results=count)
                if top_jobs:
                    await self.notifier.send_job_batch(
                        top_jobs,
                        batch_title=f"More Jobs ({count})"
                    )
                    db.mark_jobs_seen([sj.job for sj in top_jobs], notified=True)
            else:
                top_jobs = rank_jobs(all_jobs, max_results=count)
                if top_jobs:
                    await self.notifier.send_job_batch(
                        top_jobs,
                        batch_title=f"More Jobs ({count})"
                    )
                    db.mark_jobs_seen(top_jobs, notified=True)

            if not top_jobs:
                await self.notifier.send_message(
                    "😕 No matching jobs found. Try adjusting criteria."
                )

            db.mark_jobs_seen(all_jobs, notified=False)

        except Exception as e:
            await self.notifier.send_message(f"❌ Error: {e}")

    async def cmd_stop(self):
        """Pause alerts."""
        self.is_paused = True
        await self.notifier.send_message(
            "⏸️ *Alerts Paused*\n\n"
            "I won't send automatic job alerts until you resume.\n"
            "Use /resume to start receiving alerts again.\n\n"
            "_You can still use /search and /more manually._"
        )

    async def cmd_resume(self):
        """Resume alerts."""
        self.is_paused = False
        await self.notifier.send_message(
            "▶️ *Alerts Resumed*\n\n"
            "You'll receive job alerts at 8 AM & 6 PM.\n"
            "Use /stop to pause again."
        )

    async def cmd_quick(self):
        """Quick search - just titles."""
        await self.notifier.send_message("🔍 Quick search...")

        try:
            all_jobs = await scrape_all_jobs()

            if not all_jobs:
                await self.notifier.send_message("No jobs found.")
                return

            top_jobs = rank_jobs(all_jobs, max_results=5)

            if top_jobs:
                message = "📋 *Quick Results*\n\n"
                for i, job in enumerate(top_jobs, 1):
                    message += f"{i}. {job.title}\n   _{job.company} • {job.location}_\n\n"
                message += "_Use /search for full details_"
                await self.notifier.send_message(message)
            else:
                await self.notifier.send_message("No matching jobs found.")

        except Exception as e:
            await self.notifier.send_message(f"❌ Error: {e}")

    async def run(self):
        """Main bot loop - listen for commands."""
        print(f"\n{'='*50}")
        print("Job Scout Bot Listener Started")
        print(f"Listening for commands from chat: {self.chat_id}")
        print(f"{'='*50}\n")

        # Send startup message
        await self.notifier.send_message(
            "🤖 *Job Scout Bot Online*\n\n"
            "I'm now listening for commands!\n\n"
            "Try: /search, /more, /status, /help"
        )

        while True:
            try:
                updates = await self.get_updates(timeout=30)

                for update in updates:
                    message = update.get("message", {})
                    text = message.get("text", "")
                    chat_id = message.get("chat", {}).get("id")
                    message_id = message.get("message_id")

                    if text and text.startswith("/"):
                        await self.handle_command(text, chat_id, message_id)

            except Exception as e:
                print(f"Bot loop error: {e}")
                await asyncio.sleep(5)


async def main():
    """Start the bot listener."""
    bot = TelegramBotListener()
    await bot.run()


if __name__ == "__main__":
    asyncio.run(main())
