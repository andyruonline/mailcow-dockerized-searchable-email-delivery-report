#!/usr/bin/env python3
"""
Mailcow Email Delivery Report
A simple CLI tool to generate email delivery reports from a mailcow dockerized server.
"""

import argparse
import json
import sys
import subprocess
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import re


class MailcowDeliveryReport:
    """Main class for handling email delivery reports from mailcow."""
    
    def __init__(self, container_name: str = "mailcowdockerized-postfix-mailcow-1"):
        """
        Initialize the delivery report tool.
        
        Args:
            container_name: Name of the postfix container in mailcow
        """
        self.container_name = container_name
        
    def get_logs(self, lines: int = 1000) -> str:
        """
        Retrieve logs from the postfix container.
        
        Args:
            lines: Number of log lines to retrieve
            
        Returns:
            Log content as string
        """
        try:
            cmd = ["docker", "logs", "--tail", str(lines), self.container_name]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return result.stdout + result.stderr
        except subprocess.CalledProcessError as e:
            print(f"Error retrieving logs: {e}", file=sys.stderr)
            return ""
        except FileNotFoundError:
            print("Docker command not found. Is Docker installed?", file=sys.stderr)
            return ""
    
    def parse_log_entry(self, line: str) -> Optional[Dict]:
        """
        Parse a single log line into structured data.
        
        Args:
            line: Log line to parse
            
        Returns:
            Dictionary with parsed data or None if line doesn't match
        """
        # Pattern for postfix log entries
        # Example: Jan 1 12:00:00 postfix/smtp[12345]: ABC123: to=<user@domain.com>, status=sent
        patterns = {
            'sent': re.compile(
                r'(\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2}).*postfix/\w+\[(\d+)\]:\s+([A-F0-9]+):\s+to=<([^>]+)>.*status=sent'
            ),
            'deferred': re.compile(
                r'(\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2}).*postfix/\w+\[(\d+)\]:\s+([A-F0-9]+):\s+to=<([^>]+)>.*status=deferred'
            ),
            'bounced': re.compile(
                r'(\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2}).*postfix/\w+\[(\d+)\]:\s+([A-F0-9]+):\s+to=<([^>]+)>.*status=bounced'
            ),
        }
        
        for status, pattern in patterns.items():
            match = pattern.search(line)
            if match:
                timestamp = match.group(1)
                pid = match.group(2)
                queue_id = match.group(3)
                email = match.group(4)
                
                return {
                    'timestamp': timestamp,
                    'pid': pid,
                    'queue_id': queue_id,
                    'email': email,
                    'status': status,
                    'raw': line.strip()
                }
        
        return None
    
    def get_delivery_report(self, lines: int = 1000) -> List[Dict]:
        """
        Generate a delivery report from logs.
        
        Args:
            lines: Number of log lines to analyze
            
        Returns:
            List of parsed delivery entries
        """
        logs = self.get_logs(lines)
        entries = []
        
        for line in logs.split('\n'):
            parsed = self.parse_log_entry(line)
            if parsed:
                entries.append(parsed)
        
        return entries
    
    def filter_entries(self, entries: List[Dict], 
                      recipient: Optional[str] = None,
                      status: Optional[str] = None,
                      queue_id: Optional[str] = None) -> List[Dict]:
        """
        Filter delivery entries based on criteria.
        
        Args:
            entries: List of delivery entries
            recipient: Filter by recipient email
            status: Filter by delivery status
            queue_id: Filter by queue ID
            
        Returns:
            Filtered list of entries
        """
        filtered = entries
        
        if recipient:
            filtered = [e for e in filtered if recipient.lower() in e['email'].lower()]
        
        if status:
            filtered = [e for e in filtered if e['status'] == status.lower()]
        
        if queue_id:
            filtered = [e for e in filtered if e['queue_id'] == queue_id.upper()]
        
        return filtered
    
    def print_report(self, entries: List[Dict], format: str = 'table'):
        """
        Print delivery report in specified format.
        
        Args:
            entries: List of delivery entries
            format: Output format ('table', 'json', 'csv')
        """
        if not entries:
            print("No matching delivery records found.")
            return
        
        if format == 'json':
            print(json.dumps(entries, indent=2))
        elif format == 'csv':
            print("Timestamp,Queue ID,Recipient,Status")
            for entry in entries:
                print(f"{entry['timestamp']},{entry['queue_id']},{entry['email']},{entry['status']}")
        else:  # table format (default)
            print(f"\n{'Timestamp':<20} {'Queue ID':<12} {'Recipient':<35} {'Status':<10}")
            print("-" * 80)
            for entry in entries:
                timestamp = entry['timestamp'][:19] if len(entry['timestamp']) > 19 else entry['timestamp']
                recipient = entry['email'][:34] if len(entry['email']) > 34 else entry['email']
                print(f"{timestamp:<20} {entry['queue_id']:<12} {recipient:<35} {entry['status']:<10}")
            
            # Print summary
            status_counts = {}
            for entry in entries:
                status_counts[entry['status']] = status_counts.get(entry['status'], 0) + 1
            
            print("\n" + "=" * 80)
            print(f"Total: {len(entries)} deliveries")
            for status, count in sorted(status_counts.items()):
                print(f"  {status.capitalize()}: {count}")


def main():
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(
        description='Mailcow Email Delivery Report - Generate delivery reports from mailcow logs',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Get last 1000 delivery attempts
  %(prog)s
  
  # Get last 5000 delivery attempts
  %(prog)s --lines 5000
  
  # Filter by recipient
  %(prog)s --recipient user@example.com
  
  # Filter by status
  %(prog)s --status sent
  
  # Output as JSON
  %(prog)s --format json
  
  # Combine filters
  %(prog)s --recipient user@example.com --status deferred --lines 2000
        """
    )
    
    parser.add_argument(
        '--lines', '-n',
        type=int,
        default=1000,
        help='Number of log lines to analyze (default: 1000)'
    )
    
    parser.add_argument(
        '--recipient', '-r',
        type=str,
        help='Filter by recipient email address'
    )
    
    parser.add_argument(
        '--status', '-s',
        type=str,
        choices=['sent', 'deferred', 'bounced'],
        help='Filter by delivery status'
    )
    
    parser.add_argument(
        '--queue-id', '-q',
        type=str,
        help='Filter by queue ID'
    )
    
    parser.add_argument(
        '--format', '-f',
        type=str,
        choices=['table', 'json', 'csv'],
        default='table',
        help='Output format (default: table)'
    )
    
    parser.add_argument(
        '--container', '-c',
        type=str,
        default='mailcowdockerized-postfix-mailcow-1',
        help='Postfix container name (default: mailcowdockerized-postfix-mailcow-1)'
    )
    
    args = parser.parse_args()
    
    # Create reporter instance
    reporter = MailcowDeliveryReport(container_name=args.container)
    
    # Get delivery report
    print(f"Analyzing last {args.lines} log lines...", file=sys.stderr)
    entries = reporter.get_delivery_report(lines=args.lines)
    
    # Apply filters
    filtered_entries = reporter.filter_entries(
        entries,
        recipient=args.recipient,
        status=args.status,
        queue_id=args.queue_id
    )
    
    # Print report
    reporter.print_report(filtered_entries, format=args.format)


if __name__ == '__main__':
    main()
