# Job Scout Agent

## Claude Code Guidelines

**Token Efficiency:**
- Be concise. Short answers preferred.
- Skip unnecessary explanations unless asked.
- Use bullet points over paragraphs.
- Don't repeat information already in this file.
- One-line answers when possible.

**Rate Limit Protocol:**
- Monitor token usage throughout session.
- Before hitting rate limit: STOP and save all work in progress.
- Update this CLAUDE.md with any new learnings, commands, or fixes discovered.
- If implementing changes: commit or write to files before rate limit.
- Warn user when approaching limit so they can continue later.

**Session State:**
- Track what was being worked on.
- Document any pending tasks below before session ends.

### Pending Tasks
_(Updated each session as needed)_
- None

---

## Overview
Automated job scraper that finds IT Support jobs and sends alerts via Telegram with resume-based fit scoring.

## Quick Start
```bash
# Install dependencies
pip install -r requirements.txt

# Start bot listener (responds to Telegram commands)
python agent.py --listen

# Or run a one-time job search
python agent.py
```

## Telegram Commands
| Command | Description |
|---------|-------------|
| `/search` | Run job search now |
| `/more` | Get 10 more jobs |
| `/more 20` | Get 20 more jobs |
| `/status` | Bot status |
| `/stop` | Pause alerts |
| `/resume` | Resume alerts |
| `/help` | Show commands |

## CLI Options
```bash
python agent.py                     # Run job scout once
python agent.py --listen            # Start bot listener (REQUIRED for commands)
python agent.py --more              # Send 10 more jobs
python agent.py --more 20           # Send 20 more jobs
python agent.py --resume file.pdf   # Upload resume for fit scoring
python agent.py --resume-info       # Show resume status
python agent.py --current-job "IT Support Specialist"  # Set current job
python agent.py --status            # Send status to Telegram
python agent.py --test              # Test Telegram connection
```

## Resume Features
- Upload PDF or TXT resume for personalized job matching
- Fit score (0-100%) shown with each job
- Skills, experience, and certifications extracted automatically
- Career progression detection (lead/senior roles scored higher)

## Location Filtering
- **NJ (5-30 miles from Bayonne)**: Preferred
  - Close (5-15 mi): Jersey City, Hoboken, Newark, etc.
  - Medium (15-30 mi): Elizabeth, Fort Lee, Hackensack, etc.
- **NYC**: Manhattan and Brooklyn ONLY
- **Excluded**: Queens, Bronx, Staten Island, NJ >30mi

## Run as Background Service

### Option 1: Screen
```bash
screen -S jobscout
python agent.py --listen
# Press Ctrl+A, then D to detach
# Reattach: screen -r jobscout
```

### Option 2: Systemd
```bash
sudo nano /etc/systemd/system/jobscout.service
```

```ini
[Unit]
Description=Job Scout Telegram Bot
After=network.target

[Service]
ExecStart=/usr/bin/python3 /home/pi/job-scout-agent/agent.py --listen
WorkingDirectory=/home/pi/job-scout-agent
Restart=always
User=pi

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable jobscout
sudo systemctl start jobscout
sudo systemctl status jobscout
```

## Files
- `agent.py` - Main entry point
- `bot_listener.py` - Telegram command handler
- `scrapers.py` - LinkedIn, Indeed, Glassdoor scrapers
- `ranker.py` - Job scoring and filtering
- `resume_manager.py` - Resume parsing and fit scoring
- `telegram_notifier.py` - Telegram message sender
- `database.py` - SQLite job tracking
- `config.py` - Configuration

## Telegram Bot Setup
Set environment variables in `.env` file:
```bash
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
```

## Data Sources (Free)
- LinkedIn Jobs (scraping)
- Indeed Jobs (scraping)
- Glassdoor Jobs (scraping)
