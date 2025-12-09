# Mailcow Dockerized Email Delivery Report

A Python utility for analyzing Postfix mail logs from Mailcow Dockerized to generate email delivery tracking reports.

## Features

- 📊 Parse Postfix logs and extract email delivery metadata
- 🔍 Search by sender, recipient, or both
- 📅 Flexible date/time filtering (specific dates, lookback days, time ranges)
- 🎨 Color-coded output (green=sent, red=blocked)
- ⚡ Fast performance via direct Docker log file reading
- 📈 Summary statistics with email counts and date ranges
- 🔄 SendGrid routing detection

## Requirements

- Python 3.6+
- Mailcow Dockerized installation
- `sudo` access for reading Docker logs

## Installation

1. Clone this repository:

```bash
git clone https://github.com/andyruonline/mailcow-dockerized-searchable-email-delivery-report.git
cd mailcow-dockerized-searchable-email-delivery-report
```

2. Make the script executable:

```bash
chmod +x mailcow_email_delivery_report.py
```

3. (Optional) Copy to your bin directory for system-wide access:

```bash
sudo cp mailcow_email_delivery_report.py /usr/local/bin/mailcow_email_delivery_report
```

**Note:** This script requires `sudo` privileges to read Docker container logs. You can either:
- Run the script with `sudo`: `sudo ./mailcow_email_delivery_report.py`
- Add your user to the `docker` group: `sudo usermod -aG docker $USER` (requires logout/login)

## Usage

### Interactive Mode
Simply run the script with no arguments and answer the prompts:
```bash
./mailcow_email_delivery_report.py
```

### Command-Line Mode

**Search for specific email/domain:**
```bash
./mailcow_email_delivery_report.py --search peter@example.com --days 10
```

**Filter by recipient only:**
```bash
./mailcow_email_delivery_report.py --search example.com --type recipient --days all
```

**Specific date range:**
```bash
./mailcow_email_delivery_report.py --date "8 Dec"
```

**Date and time (shows from that time onwards):**
```bash
./mailcow_email_delivery_report.py --date "8 Dec" --time "23:50:00"
```

**Test mode (uses sample log file):**
```bash
./mailcow_email_delivery_report.py --test --search peter --days 2
```

### Command-Line Options

```
  --search, -s SEARCH   Search term (email, domain, or partial)
  --type, -t TYPE       Search type: sender, recipient, or both (default: both)
  --days, -d DAYS       Number of days to look back, or "all" for no date filter
  --date DATE           Specific date filter (e.g. "8 Dec", "Dec 8", "8 Dec 2025")
  --time TIME           Specific time filter (e.g. "23:46:06"). Shows emails from this time onwards
  --test                Use test log file instead of live Docker logs
```

## Configuration

Edit the script to customize these settings:

```python
MAILCOW_DIR = "/opt/mailcow-dockerized"
TEST_LOG_FILE = "mailcow-log-sample.log"
DOCKER_LOG_PATH = "/var/lib/docker/containers"
```

## How It Works

1. **Log Retrieval**: Directly reads Docker container JSON log files for speed (falls back to `docker compose logs` if needed)
2. **Parsing**: Uses regex to extract Postfix queue IDs, email addresses, sizes, timestamps, and status
3. **Aggregation**: Groups log lines by queue ID to build complete message records
4. **Filtering**: Applies search and date/time filters
5. **Display**: Outputs formatted table with color coding and summary statistics

## Output Format

```
Time            | From                           | To                                  | Size     | Status   | SG
-----------------------------------------------------------------------------------------------------------------
8 Dec 23:50:01  | sender@example.com             | recipient@example.com               | 150KB    | sent     | No
8 Dec 23:52:33  | blocked@spam.com               | target@example.com                  | -        | blocked  | No

Total matching emails: 2
Search criteria: All containing 'example.com'
Date filter applied: 8 Dec
Date range in results: 8 Dec 23:50:01 to 8 Dec 23:52:33
```

## Date/Time Filtering

- **Lookback days**: `--days 7` shows last 7 days
- **Specific date**: `--date "8 Dec"` shows entire day
- **Date + time**: `--date "8 Dec" --time "12:00:00"` shows from 12pm onwards on Dec 8, plus all subsequent dates
- **Australian format**: Dates display as "8 Dec 23:50:01" (day first)

## Performance

- Direct Docker log reading: **~1 second** for large log files
- Docker compose fallback: **~30-60 seconds**

## License

MIT License - see LICENSE file for details

## Contributing

Pull requests welcome! Please open an issue first to discuss major changes.

## Author

Created for Mailcow Dockerized email server administration and troubleshooting.
