#!/usr/bin/env python3
"""
Mailcow Email Delivery Report Generator
Parses Postfix logs to extract email delivery tracking information
"""
import subprocess
import re
import sys
import glob
import argparse
from datetime import datetime, timedelta

# Configuration
MAILCOW_DIR = "/opt/mailcow-dockerized"
TEST_LOG_FILE = "mailcow-log-sample.log"
DOCKER_LOG_PATH = "/var/lib/docker/containers"

# ANSI color codes
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    RESET = '\033[0m'


def get_logs(use_test_mode):
    """Fetch logs from either test file or Docker container log files"""
    if use_test_mode:
        print(f"[TEST MODE] Reading from {TEST_LOG_FILE}\n")
        with open(TEST_LOG_FILE, 'r') as f:
            return f.read()
    else:
        # Find and read the postfix-mailcow container log file
        try:
            import json
            
            # Find all *-json.log files in Docker containers directory
            result = subprocess.run(
                ["sudo", "find", DOCKER_LOG_PATH, "-name", "*-json.log", "-type", "f"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode != 0:
                raise Exception("find command failed")
            
            # Check each log file for Postfix data (stop at first match)
            for log_file in result.stdout.strip().split('\n'):
                if not log_file:
                    continue
                
                # Quick check: read first 20 lines to see if it's a Postfix log
                check = subprocess.run(
                    ["sudo", "head", "-20", log_file],
                    capture_output=True,
                    text=True
                )
                
                if check.returncode == 0 and 'postfix' in check.stdout:
                    # Found the postfix log, now read it and extract the log content
                    read = subprocess.run(
                        ["sudo", "cat", log_file],
                        capture_output=True,
                        text=True,
                        timeout=10
                    )
                    
                    if read.returncode == 0:
                        # Parse JSON and extract log lines
                        logs = []
                        for line in read.stdout.strip().split('\n'):
                            if not line:
                                continue
                            try:
                                data = json.loads(line)
                                if 'log' in data:
                                    logs.append(data['log'].rstrip('\n'))
                            except:
                                pass
                        
                        return '\n'.join(logs)
            
            # Fallback to docker compose logs if no suitable file found
            print("[INFO] Reading logs via docker compose (this may take a moment)...")
            cmd = ["sudo", "docker", "compose", "logs", "postfix-mailcow", "-n5000"]
            result = subprocess.run(cmd, cwd=MAILCOW_DIR, capture_output=True, text=True, timeout=120)
            return result.stdout
            
        except Exception as e:
            print(f"[INFO] Could not read Docker log files directly: {e}")
            print("[INFO] Reading logs via docker compose (this may take a moment)...")
            cmd = ["sudo", "docker", "compose", "logs", "postfix-mailcow", "-n5000"]
            result = subprocess.run(cmd, cwd=MAILCOW_DIR, capture_output=True, text=True, timeout=120)
            return result.stdout


def extract_queue_id(line):
    """Extract Postfix queue ID from log line (10-12 hex characters)"""
    match = re.search(r'\b([A-F0-9]{10,12})\b', line)
    return match.group(1) if match else None


def extract_field(line, pattern):
    """Extract a field from log line using regex pattern"""
    match = re.search(pattern, line)
    return match.group(1) if match else None


def extract_timestamp(line):
    """Extract syslog timestamp from log line and format as Australian style (9 Dec HH:MM:SS)"""
    match = re.search(r'([A-Z][a-z]{2})\s+(\d+)\s+(\d{2}:\d{2}:\d{2})', line)
    if match:
        month = match.group(1)
        day = int(match.group(2))
        time = match.group(3)
        # Australian format: day month time
        return f"{day} {month} {time}"
    return None


def is_blocked(line):
    """Check if log line indicates a blocked/rejected message"""
    return ("NOQUEUE: reject" in line or 
            "NOQUEUE: filter" in line or 
            "milter-reject" in line or
            "status=bounced" in line or
            "status=deferred" in line)


def is_sendgrid(line):
    """Check if message is routed via SendGrid"""
    return "smtp_via_transport_maps:smtp.sendgrid.net" in line


def format_size(size_str):
    """Convert byte size to kilobytes"""
    if size_str == "-":
        return "-"
    
    try:
        size_bytes = int(size_str)
        size_kb = size_bytes / 1024
        return f"{int(size_kb)}KB"
    except (ValueError, TypeError):
        return "-"


def parse_date_time_for_comparison(date_str, time_str):
    """Parse date and time strings into a comparable datetime object
    
    Args:
        date_str: Date in format like "7 Dec" or "Dec 7"
        time_str: Time in format like "12:00:00"
    
    Returns:
        datetime object for comparison, or None if parsing fails
    """
    if not date_str:
        return None
    
    parts = date_str.split()
    num_part = None
    month_part = None
    
    for part in parts:
        if part.isdigit() and len(part) <= 2:
            num_part = int(part)
        elif re.match(r'[A-Z][a-z]{2}', part):
            month_part = part
    
    if not (num_part and month_part):
        return None
    
    # Use current year for comparison
    year = datetime.now().year
    month_num = datetime.strptime(month_part, '%b').month
    
    # Parse time if provided, otherwise use 00:00:00
    if time_str:
        time_parts = time_str.split(':')
        hour = int(time_parts[0]) if len(time_parts) > 0 else 0
        minute = int(time_parts[1]) if len(time_parts) > 1 else 0
        second = int(time_parts[2]) if len(time_parts) > 2 else 0
    else:
        hour = minute = second = 0
    
    try:
        return datetime(year, month_num, num_part, hour, minute, second)
    except ValueError:
        return None


def parse_timestamp_from_line(line):
    """Extract timestamp from log line and convert to datetime object
    
    Returns:
        datetime object, or None if parsing fails
    """
    match = re.search(r'([A-Z][a-z]{2})\s+(\d+)\s+(\d{2}):(\d{2}):(\d{2})', line)
    if not match:
        return None
    
    month_str = match.group(1)
    day = int(match.group(2))
    hour = int(match.group(3))
    minute = int(match.group(4))
    second = int(match.group(5))
    
    year = datetime.now().year
    month_num = datetime.strptime(month_str, '%b').month
    
    try:
        return datetime(year, month_num, day, hour, minute, second)
    except ValueError:
        return None


def should_include_log_line(line, start_datetime):
    """Check if log line is on or after the start datetime
    
    Args:
        line: Log line to check
        start_datetime: Starting datetime (from --date and --time)
    
    Returns:
        True if line should be included, False otherwise
    """
    if not start_datetime:
        return True  # No filter, include everything
    
    line_datetime = parse_timestamp_from_line(line)
    if not line_datetime:
        return False  # Can't parse, exclude
    
    return line_datetime >= start_datetime


def parse_date_filter(date_input, time_input=None):
    """Parse date filter input and return matching patterns
    
    This function is now used only for lookback days (numeric input).
    For specific dates with times, we use datetime comparison instead.
    
    Supports:
    - Single number (lookback X days from today)
    - Empty string (no filter)
    
    Returns: list of date patterns to match in logs, or None for no filter
    """
    if not date_input:
        return None
    
    # Check if it's a number (lookback days)
    try:
        days_back = int(date_input)
        patterns = []
        for i in range(days_back + 1):
            date_obj = datetime.now() - timedelta(days=i)
            day = date_obj.day
            month = date_obj.strftime('%b')
            
            # Syslog format: days 1-9 have TWO spaces, days 10+ have ONE space
            if day < 10:
                patterns.append(f"{month}  {day}")  # Two spaces for single-digit days
            else:
                patterns.append(f"{month} {day}")   # One space for double-digit days
        return patterns
    except ValueError:
        pass
    
    # Not a number - will use datetime comparison instead
    return None


def process_logs(lines, date_filter, time_filter=None):
    """Process log lines and aggregate message data by queue ID"""
    messages = {}
    
    # Try to parse date/time for comparison (specific date + time)
    start_datetime = parse_date_time_for_comparison(date_filter, time_filter) if date_filter else None
    
    # For numeric lookback days, use pattern matching instead
    date_patterns = None
    if date_filter and not start_datetime:
        date_patterns = parse_date_filter(date_filter, time_filter)
    
    for line in lines:
        # Apply date/time filter
        if start_datetime:
            # Use datetime comparison for specific date + optional time
            if not should_include_log_line(line, start_datetime):
                continue
        elif date_patterns:
            # Use pattern matching for lookback days
            if not any(pattern in line for pattern in date_patterns):
                continue
        
        # Extract queue ID - process all lines to build complete message data
        qid = extract_queue_id(line)
        if not qid:
            continue
        
        # Initialize message entry if new queue ID
        if qid not in messages:
            messages[qid] = {
                "from": "-",
                "to": "-",
                "size": "-",
                "status": "-",
                "sg": "No",
                "time": "-"
            }
        
        # Handle blocked messages (completely replace entry)
        if is_blocked(line):
            messages[qid] = {
                "from": extract_field(line, r'from=<([^>]*)>') or "-",
                "to": extract_field(line, r'to=<([^>]*)>') or "-",
                "size": "-",  # Blocked messages don't have size info
                "status": "blocked",
                "sg": "Yes" if is_sendgrid(line) else "No",
                "time": date_filter if date_filter else "-"
            }
            continue
        
        # Extract fields from standard message lines
        from_addr = extract_field(line, r'from=<([^>]*)>')
        if from_addr:
            messages[qid]["from"] = from_addr
        
        to_addr = extract_field(line, r'to=<([^>]*)>')
        if to_addr:
            messages[qid]["to"] = to_addr
        
        size = extract_field(line, r'size=(\d+)')
        if size:
            messages[qid]["size"] = size
        
        if "status=sent" in line:
            messages[qid]["status"] = "sent"
        
        if is_sendgrid(line):
            messages[qid]["sg"] = "Yes"
        
        # Extract timestamp only if not already set
        if messages[qid]["time"] == "-":
            timestamp = extract_timestamp(line)
            if timestamp:
                messages[qid]["time"] = timestamp
    
    return messages


def print_report(messages, search_term, search_type, date_filter, status_filter=None):
    """Format and print the email delivery report"""
    # Filter out messages with no useful data (all fields blank)
    useful_messages = {
        qid: info for qid, info in messages.items()
        if info["from"] != "-" or info["to"] != "-" or info["size"] != "-" or info["status"] != "-"
    }
    
    # Apply search filter based on type
    if search_term:
        search_lower = search_term.lower()
        filtered_messages = {}
        for qid, info in useful_messages.items():
            if search_type == "sender":
                # Only check if from field exists
                if info["from"] != "-" and search_lower in info["from"].lower():
                    filtered_messages[qid] = info
            elif search_type == "recipient":
                # Only check if to field exists
                if info["to"] != "-" and search_lower in info["to"].lower():
                    filtered_messages[qid] = info
            else:  # both
                from_match = info["from"] != "-" and search_lower in info["from"].lower()
                to_match = info["to"] != "-" and search_lower in info["to"].lower()
                if from_match or to_match:
                    filtered_messages[qid] = info
        useful_messages = filtered_messages
    
    # Apply status filter if specified
    if status_filter:
        if status_filter == 'success':
            useful_messages = {qid: info for qid, info in useful_messages.items() if info["status"] == "sent"}
        elif status_filter == 'blocked':
            useful_messages = {qid: info for qid, info in useful_messages.items() if info["status"] == "blocked"}
        elif status_filter == 'unknown':
            useful_messages = {qid: info for qid, info in useful_messages.items() if info["status"] == "-"}
    
    # Header
    header = f"{'Time':<15} | {'From':<30} | {'To':<35} | {'Size':<8} | {'Status':<8} | {'SG':<2}"
    print("\n" + header)
    print("-" * len(header))
    
    # Extract and track dates
    dates = []
    
    # Data rows
    for qid, info in useful_messages.items():
        # Track dates
        if info["time"] != "-":
            dates.append(info["time"])
        
        # Determine color based on status
        color = Colors.RESET
        if info["status"] == "blocked":
            color = Colors.RED
        elif info["status"] == "sent":
            color = Colors.GREEN
        
        # Format size for human-readable display
        readable_size = format_size(info["size"])
        
        print(f"{color}{info['time']:<15} | {info['from']:<30} | {info['to']:<35} | "
              f"{readable_size:<8} | {info['status']:<8} | {info['sg']:<2}{Colors.RESET}")
    
    # Summary statistics
    print("-" * len(header))
    
    # Calculate status counts
    sent_count = sum(1 for msg in useful_messages.values() if msg['status'] == 'sent')
    blocked_count = sum(1 for msg in useful_messages.values() if msg['status'] == 'blocked')
    unknown_count = sum(1 for msg in useful_messages.values() if msg['status'] == '-')
    
    print(f"\nTotal matching emails: {len(useful_messages)}")
    print(f"  - Sent/Received successfully: {sent_count}")
    print(f"  - Blocked: {blocked_count}")
    if unknown_count > 0:
        print(f"  - Unknown status: {unknown_count}")
    
    # Format search type for display
    search_display = "all" if search_type == "both" else search_type
    
    if search_term:
        print(f"Search criteria: {search_display.capitalize()} containing '{search_term}'")
    else:
        print(f"Search criteria: {search_display.capitalize()} (all emails)")
    
    if status_filter:
        print(f"Status filter: {status_filter}")
    
    if date_filter:
        print(f"Date filter applied: {date_filter}")
    
    if dates:
        dates_sorted = sorted(set(dates))
        print(f"Date range in results: {dates_sorted[0]} to {dates_sorted[-1]}")
    
    print("\n=== End of Report ===\n")


def main():
    """Main entry point"""
    # Set up argument parser
    parser = argparse.ArgumentParser(
        description='Mailcow Email Delivery Report Generator',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --search peter@electromech --days 10
  %(prog)s --search canvasu --type recipient --days all
  %(prog)s --search test@example.com --date "8 Dec"
  %(prog)s --search peter --date "8 Dec 2025" --time "23:46:06"
  %(prog)s --date "Dec 8" --time "15:30:00"
  %(prog)s --test --days 2
        """
    )
    
    parser.add_argument('--search', '-s', 
                       default='',
                       help='Search term (email, domain, or partial). Leave blank for all emails.')
    
    parser.add_argument('--type', '-t',
                       choices=['sender', 'recipient', 'both'],
                       default='both',
                       help='Search type: sender, recipient, or both (default: both)')
    
    parser.add_argument('--status',
                       choices=['success', 'blocked', 'unknown'],
                       help='Filter by delivery status: success, blocked, or unknown')
    
    parser.add_argument('--days', '-d',
                       help='Number of days to look back, or "all" for no date filter')
    
    parser.add_argument('--date',
                       help='Specific date filter (e.g. "8 Dec", "Dec 8", "8 Dec 2025")')
    
    parser.add_argument('--time',
                       help='Specific time filter to combine with --date (e.g. "23:46:06"). Shows all emails from this time onward on the specified date, plus all subsequent dates.')
    
    parser.add_argument('--test',
                       action='store_true',
                       help='Use test log file instead of live Docker logs')
    
    args = parser.parse_args()
    
    # Determine if we're in interactive or command-line mode
    interactive_mode = not any([args.search, args.days, args.date])
    
    if interactive_mode:
        # Interactive mode - prompt for inputs
        print("\n=== Mailcow Email Tracking Report ===\n")
        
        search_term = input("Search for (email, domain, or partial): ").strip()
        
        # Get search type
        print("\nSearch type:")
        print("1. Sender (FROM address)")
        print("2. Recipient (TO address)")
        print("3. Both sender and recipient")
        search_choice = input("Choose [1-3] (default: 3): ").strip() or "3"
        
        search_type_map = {"1": "sender", "2": "recipient", "3": "both"}
        search_type = search_type_map.get(search_choice, "both")
        
        # Get status filter
        print("\nFilter by delivery status:")
        print("1. Success (sent/received)")
        print("2. Blocked")
        print("3. Unknown")
        print("4. All statuses (no filter)")
        status_choice = input("Choose [1-4] (default: 4): ").strip() or "4"
        
        status_map = {"1": "success", "2": "blocked", "3": "unknown", "4": None}
        status_filter = status_map.get(status_choice, None)
        
        date_filter = input("\nFilter by date (e.g. '5 Dec', 'Dec 5', '5 Dec 2025', or '3' for last 3 days, or blank): ").strip()
        time_filter = input("Filter by time (e.g. '23:46:06' or blank): ").strip() or None
    else:
        # Command-line mode - use arguments
        print("\n=== Mailcow Email Tracking Report ===\n")
        
        search_term = args.search
        search_type = args.type
        status_filter = args.status
        time_filter = args.time
        
        # Handle date filter
        if args.date:
            date_filter = args.date
        elif args.days:
            if args.days.lower() == 'all':
                date_filter = ''
            else:
                date_filter = args.days
        else:
            date_filter = ''
    
    # Determine execution mode
    use_test_mode = args.test
    
    # Fetch logs
    logs = get_logs(use_test_mode)
    lines = logs.splitlines()
    
    # Process logs (date filtering only)
    messages = process_logs(lines, date_filter, time_filter)
    
    # Print report (search and status filtering)
    print_report(messages, search_term, search_type, date_filter, status_filter)


if __name__ == "__main__":
    main()
