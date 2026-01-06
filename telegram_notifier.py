"""Telegram notification handler."""
import asyncio
from typing import List
import httpx

from config import config
from scrapers import Job


class TelegramNotifier:
    """Send job alerts via Telegram."""

    def __init__(self):
        self.bot_token = config.telegram.bot_token
        self.chat_id = config.telegram.chat_id
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"

    async def send_message(self, text: str, parse_mode: str = "Markdown") -> bool:
        """Send a message to the configured chat."""
        url = f"{self.base_url}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": parse_mode,
            "disable_web_page_preview": True,
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, json=payload)
                return response.status_code == 200
        except Exception as e:
            print(f"Telegram error: {e}")
            return False

    async def send_job_alert(self, job: Job) -> bool:
        """Send a single job alert."""
        return await self.send_message(job.to_telegram_message())

    async def send_job_batch(self, jobs: List[Job], batch_title: str = None) -> int:
        """Send multiple jobs as a batch with summary."""
        if not jobs:
            return 0

        sent_count = 0

        # Send header
        header = f"🔔 *Job Scout Alert*\n"
        if batch_title:
            header += f"_{batch_title}_\n"
        header += f"\n📊 Found *{len(jobs)}* new job(s) matching your criteria:\n"
        header += "─" * 20

        await self.send_message(header)
        await asyncio.sleep(0.5)  # Rate limiting

        # Send each job
        for i, job in enumerate(jobs):
            success = await self.send_job_alert(job)
            if success:
                sent_count += 1

            # Rate limiting - Telegram allows ~30 msgs/sec but be conservative
            await asyncio.sleep(0.3)

            # Add separator every 5 jobs
            if (i + 1) % 5 == 0 and i + 1 < len(jobs):
                await self.send_message("─" * 20)
                await asyncio.sleep(0.3)

        # Send footer
        footer = f"\n✅ Sent {sent_count}/{len(jobs)} jobs\n"
        footer += "💡 _Reply /stop to pause alerts_"
        await self.send_message(footer)

        return sent_count

    async def send_no_jobs_message(self) -> bool:
        """Notify when no new jobs found."""
        message = (
            "🔍 *Job Scout Update*\n\n"
            "No new jobs found matching your criteria since last check.\n\n"
            "I'm searching for:\n"
            f"• {', '.join(config.preferences.roles[:3])}...\n"
            f"• Location: {config.preferences.location}\n"
            f"• Salary: ${config.preferences.min_salary:,}+\n\n"
            "_I'll check again at the next scheduled time._"
        )
        return await self.send_message(message)

    async def send_error_message(self, error: str) -> bool:
        """Notify about an error."""
        message = f"⚠️ *Job Scout Error*\n\n{error}\n\n_Will retry at next scheduled run._"
        return await self.send_message(message)

    async def send_welcome_message(self) -> bool:
        """Send initial setup confirmation."""
        roles_list = "\n".join(f"  • {role}" for role in config.preferences.roles[:5])
        if len(config.preferences.roles) > 5:
            roles_list += f"\n  • ... and {len(config.preferences.roles) - 5} more"

        message = (
            "🎉 *Job Scout Agent Activated!*\n\n"
            "I'll send you job alerts twice daily (8 AM & 6 PM).\n\n"
            "*Your Search Criteria:*\n"
            f"📋 Roles:\n{roles_list}\n\n"
            f"📍 Location: {config.preferences.location} (Hybrid + Remote)\n"
            f"💰 Min Salary: ${config.preferences.min_salary:,}\n"
            f"📅 Job Age: Last {config.preferences.max_days_old} days\n"
            f"🔍 Sources: {', '.join(s.title() for s in config.scraper.sources)}\n\n"
            "*Commands:*\n"
            "/status - Check agent status\n"
            "/search - Run search now\n"
            "/stop - Pause alerts\n\n"
            "_Happy job hunting!_ 🚀"
        )
        return await self.send_message(message)


async def test_telegram():
    """Test Telegram connection."""
    notifier = TelegramNotifier()
    success = await notifier.send_message("🧪 Test message from Job Scout Agent!")
    print(f"Telegram test: {'Success' if success else 'Failed'}")
    return success


if __name__ == "__main__":
    asyncio.run(test_telegram())
