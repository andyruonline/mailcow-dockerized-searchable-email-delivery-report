#!/usr/bin/env python3
"""
Mailcow Email Delivery Report Generator
Parses Postfix logs to extract email delivery tracking information
"""
import subprocess
import re
import sys
import glob
from datetime import datetime

# Configuration
MAILCOW_DIR = "/opt/mailcow-dockerized"
TEST_LOG_FILE = "postfix-log-sample.log"
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
        # Find the postfix-mailcow container log file
        try:
            # Search for postfix container directory
            containers = glob.glob(f"{DOCKER_LOG_PATH}/*/")
            postfix_log = None
            
            for container_dir in containers:
                # Read the container config to find postfix-mailcow
                config_file = f"{container_dir}config.v2.json"
                try:
                    with open(config_file, 'r') as f:
                        config = f.read()
                        if 'postfix-mailcow' in config:
                            postfix_log = f"{container_dir}-json.log"
                            break
                except:
                    continue
            
            if not postfix_log or not glob.glob(postfix_log):
                print("[ERROR] Could not find postfix-mailcow container log file")
                print("Falling back to docker compose logs...")
                cmd = ["sudo", "docker", "compose", "logs", "postfix-mailcow", "-n5000"]
                result = subprocess.run(cmd, cwd=MAILCOW_DIR, capture_output=True, text=True)
                return result.stdout
            
            # Read the log file with sudo
            result = subprocess.run(
                ["sudo", "cat", postfix_log],
                capture_output=True,
                text=True
            )
            return result.stdout
        except Exception as e:
            print(f"[ERROR] Failed to read Docker logs: {e}")
            print("Falling back to docker compose logs...")
            cmd = ["sudo", "docker", "compose", "logs", "postfix-mailcow", "-n5000"]
            result = subprocess.run(cmd, cwd=MAILCOW_DIR, capture_output=True, text=True)
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
    """Extract syslog timestamp from log line"""
    match = re.search(r'([A-Z][a-z]{2}\s+\d+\s+\d{2}:\d{2}:\d{2})', line)
    return match.group(1) if match else None


def is_blocked(line):
    """Check if log line indicates a blocked message"""
    return "NOQUEUE: reject" in line or "NOQUEUE: filter" in line


def is_sendgrid(line):
    """Check if message is routed via SendGrid"""
    return "smtp_via_transport_maps:smtp.sendgrid.net" in line


def process_logs(lines, search_term, date_filter):
    """Process log lines and aggregate message data by queue ID"""
    messages = {}
    
    for line in lines:
        # Apply search and date filters
        if search_term.lower() not in line.lower():
            continue
        if date_filter and date_filter not in line:
            continue
        
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


def print_report(messages):
    """Format and print the email delivery report"""
    # Filter out messages with no useful data (all fields blank)
    useful_messages = {
        qid: info for qid, info in messages.items()
        if info["from"] != "-" or info["to"] != "-" or info["size"] != "-" or info["status"] != "-"
    }
    
    # Header
    header = f"{'Time':<15} | {'From':<30} | {'To':<35} | {'Size':<8} | {'Status':<8} | {'SG':<2}"
    print("\n" + header)
    print("-" * len(header))
    
    # Data rows
    for qid, info in useful_messages.items():
        # Determine color based on status
        color = Colors.RESET
        if info["status"] == "blocked":
            color = Colors.RED
        elif info["status"] == "sent":
            color = Colors.GREEN
        
        print(f"{color}{info['time']:<15} | {info['from']:<30} | {info['to']:<35} | "
              f"{info['size']:<8} | {info['status']:<8} | {info['sg']:<2}{Colors.RESET}")
    
    print("\n=== End of Report ===\n")


def main():
    """Main entry point"""
    print("\n=== Mailcow Email Tracking Report ===\n")
    
    # Get user input
    search_term = input("Search for (email, domain, or partial): ").strip()
    date_filter = input("Filter by date (e.g. 'Dec  5' or blank): ").strip()
    
    # Determine execution mode
    use_test_mode = "--test" in sys.argv
    
    # Fetch logs
    logs = get_logs(use_test_mode)
    lines = logs.splitlines()
    
    # Process logs
    messages = process_logs(lines, search_term, date_filter)
    
    # Print report
    print_report(messages)


if __name__ == "__main__":
    main()
