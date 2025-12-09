# Mailcow Email Delivery Report - AI Coding Agent Instructions

## Project Overview
This is a standalone Python utility that analyzes Postfix mail logs from a Mailcow Docker container to generate email delivery tracking reports. It parses raw Docker logs to extract message metadata and their delivery status.

**Key Goal:** Extract email delivery intelligence (sender, recipient, size, status, SendGrid routing) from unstructured Postfix logs.

## Architecture & Data Flow

### Core Components
- **Log Source:** Postfix logs from `postfix-mailcow` Docker container via `docker compose logs`
- **Log Parser:** Regex-based extraction of Postfix queue IDs and message metadata
- **Message Aggregator:** Dictionary keyed by queue ID to group related log lines
- **Report Generator:** Formatted table output with ANSI color coding

### Data Structures
```python
messages = {
    "QUEUEID": {
        "from": "sender@domain.com",
        "to": "recipient@domain.com", 
        "size": "12345",
        "status": "sent|blocked",
        "sg": "Yes|No",  # SendGrid routing detection
        "time": "Dec  5 12:34:56"
    }
}
```

### Log Line Handling
1. **Filter phase:** Match search term and optional date filter (user input)
2. **Queue ID extraction:** Regex `\b([A-F0-9]{10,12})\b` finds Postfix queue IDs
3. **Blocked detection:** "NOQUEUE: reject" or "NOQUEUE: filter" creates special entries
4. **Standard messages:** Extract from/to/size/status from repeated log entries with same queue ID
5. **SendGrid detection:** Look for `smtp_via_transport_maps:smtp.sendgrid.net` in logs

## Critical Patterns & Conventions

### Regex Patterns (Non-negotiable)
- Queue ID: `\b([A-F0-9]{10,12})\b` - exactly 10-12 hex characters
- Email extraction: `from=<([^>]*)>` and `to=<([^>]*)>` - email inside angle brackets
- Size: `size=(\d+)` - numeric bytes
- DateTime: `([A-Z][a-z]{2}\s+\d+\s+\d{2}:\d{2}:\d{2})` - syslog format (Dec  5 12:34:56)

### Message Initialization Strategy
Messages are keyed by queue ID. A new queue ID creates a dict with default values (`"-"` for unknown). Blocked messages overwrite the entire entry to prevent partial data leakage.

### Output Formatting
- Fixed-width columns with `:<15` style padding
- Status determines color: `RED` (blocked), `GREEN` (sent), `RESET` (default)
- Header dynamically calculates separator length: `print("-"*len(header))`

## Environment & Execution

### Prerequisites
- **Execution:** Requires `sudo` access (Docker calls must run as root)
- **Docker Context:** Script runs docker commands with `cwd=MAILCOW_DIR` ("/opt/mailcow-dockerized")
- **No external dependencies:** Uses only stdlib (subprocess, re, datetime)

### Running the Script
```bash
# Interactive mode - prompts for search term and optional date filter
python3 mailcow_email_delivery_report.py

# Example inputs:
# Search for: peter@example.com
# Filter by date: Dec  5
```

## Common Development Tasks

### Adding New Fields to Reports
1. Add key to default dict initialization (line 38)
2. Add extraction regex in standard message handler (lines 56-72)
3. Add column to header format string (line 75)
4. Add print field to output (line 84)

### Modifying Log Parsing Logic
- Log source: Change `cmd` list (line 23) to fetch different container/log volume
- Search behavior: User input is case-insensitive (`search.lower()` on line 31)
- Date filtering: Substring match (line 32), no date parsing - user provides syslog format

### Testing Against Sample Logs
Sample logs provided in repo:
- `postfix-log-sample.log` - Full Postfix log excerpt (~2000 lines)
- `status-only-lines.log` - Filtered status lines for pattern validation
- `trimmed-log-sample.log` - Condensed test cases

Redirect stdin for testing:
```bash
echo -e "test@example.com\nDec  5" | python3 mailcow_email_delivery_report.py
```

## Important Notes for Extensions

### Known Limitations
- DateTime parsing is syslog-only (no year component) - appropriate for same-year log analysis
- Blocked messages don't track size (inherently unavailable in NOQUEUE lines)
- No persistent storage - generates ephemeral reports from live Docker logs
- Queue ID extraction may match false positives in message bodies (rare)

### Before Making Changes
- Test against all sample logs to ensure patterns still match
- Verify ANSI color codes render in target terminal
- Confirm sudo docker calls work in your Mailcow environment
