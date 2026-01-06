# Job Scout Agent

Automated job scraper that sends daily alerts via Telegram.

## Features

- Scrapes LinkedIn and Indeed
- Filters by role, location, salary
- Deduplicates jobs across runs
- Sends formatted Telegram alerts
- Tracks all seen jobs in SQLite

## Setup

```bash
cd job-scout-agent
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Configuration

Edit `config.py` to customize:
- Target job roles
- Location preferences
- Minimum salary
- Telegram credentials

## Usage

```bash
# First run (sends welcome message)
python agent.py --welcome

# Regular run
python agent.py

# Check status
python agent.py --status

# Test Telegram
python agent.py --test
```

## Scheduled Runs

Add to crontab (`crontab -e`):

```cron
# Job Scout - 8 AM and 6 PM daily
0 8 * * * cd /path/to/job-scout-agent && ./venv/bin/python agent.py >> logs/scout.log 2>&1
0 18 * * * cd /path/to/job-scout-agent && ./venv/bin/python agent.py >> logs/scout.log 2>&1
```

## Search Criteria

| Setting | Value |
|---------|-------|
| Roles | IT Support, CX Support Lead, AI Integration Support |
| Location | New York Metro (hybrid + remote) |
| Level | Entry & Mid Level |
| Salary | $70k+ |
| Sources | LinkedIn + Indeed |
| Alerts | 8 AM & 6 PM daily |

## Telegram Commands

- `/status` - Check agent status
- `/search` - Trigger manual search
- `/stop` - Pause alerts
