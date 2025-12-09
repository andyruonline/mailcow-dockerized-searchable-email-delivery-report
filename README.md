# mailcow-email-delivery-report

A simple CLI email delivery report for mailcow dockerized. Built with Python.

## Overview

This tool provides a command-line interface to generate email delivery reports from a mailcow dockerized server. It analyzes Postfix logs to provide insights into email delivery status, including sent, deferred, and bounced messages.

## Features

- 📊 **Delivery Reports**: View email delivery attempts with status information
- 🔍 **Search & Filter**: Filter by recipient, status, or queue ID
- 📝 **Multiple Formats**: Output in table, JSON, or CSV format
- 🚀 **Easy to Use**: Simple CLI with intuitive options
- 🐳 **Docker Integration**: Works directly with mailcow Docker containers

## Requirements

- Python 3.6 or higher
- Docker access on the mailcow server
- Access to the mailcow Postfix container

## Installation

1. Clone this repository:
```bash
git clone https://github.com/andyruonline/mailcow-email-delivery-report.git
cd mailcow-email-delivery-report
```

2. Make the script executable:
```bash
chmod +x mailcow_delivery_report.py
```

3. (Optional) Create a symbolic link for easier access:
```bash
sudo ln -s $(pwd)/mailcow_delivery_report.py /usr/local/bin/mailcow-report
```

## Usage

### Basic Usage

Get a delivery report for the last 1000 log entries:
```bash
./mailcow_delivery_report.py
```

Or if you created a symbolic link:
```bash
mailcow-report
```

### Options

```
usage: mailcow_delivery_report.py [-h] [--lines LINES] [--recipient RECIPIENT]
                                   [--status {sent,deferred,bounced}]
                                   [--queue-id QUEUE_ID]
                                   [--format {table,json,csv}]
                                   [--container CONTAINER]

optional arguments:
  -h, --help            show this help message and exit
  --lines LINES, -n LINES
                        Number of log lines to analyze (default: 1000)
  --recipient RECIPIENT, -r RECIPIENT
                        Filter by recipient email address
  --status {sent,deferred,bounced}, -s {sent,deferred,bounced}
                        Filter by delivery status
  --queue-id QUEUE_ID, -q QUEUE_ID
                        Filter by queue ID
  --format {table,json,csv}, -f {table,json,csv}
                        Output format (default: table)
  --container CONTAINER, -c CONTAINER
                        Postfix container name (default: mailcowdockerized-postfix-mailcow-1)
```

### Examples

**Get the last 5000 delivery attempts:**
```bash
./mailcow_delivery_report.py --lines 5000
```

**Filter by recipient email:**
```bash
./mailcow_delivery_report.py --recipient user@example.com
```

**Filter by delivery status:**
```bash
./mailcow_delivery_report.py --status sent
```

**Show only deferred messages:**
```bash
./mailcow_delivery_report.py --status deferred
```

**Output as JSON:**
```bash
./mailcow_delivery_report.py --format json
```

**Output as CSV:**
```bash
./mailcow_delivery_report.py --format csv > deliveries.csv
```

**Combine multiple filters:**
```bash
./mailcow_delivery_report.py --recipient user@example.com --status deferred --lines 2000
```

**Use a custom container name:**
```bash
./mailcow_delivery_report.py --container my-custom-postfix-container
```

## Output Formats

### Table Format (Default)

```
Timestamp            Queue ID     Recipient                           Status    
--------------------------------------------------------------------------------
Dec  9 10:15:42      A1B2C3D4E5F  user@example.com                    sent      
Dec  9 10:15:43      B2C3D4E5F6A  another@domain.org                  deferred  
Dec  9 10:15:44      C3D4E5F6A7B  test@mail.com                       bounced   

================================================================================
Total: 3 deliveries
  Bounced: 1
  Deferred: 1
  Sent: 1
```

### JSON Format

```json
[
  {
    "timestamp": "Dec  9 10:15:42",
    "pid": "12345",
    "queue_id": "A1B2C3D4E5F",
    "email": "user@example.com",
    "status": "sent",
    "raw": "Dec  9 10:15:42 postfix/smtp[12345]: A1B2C3D4E5F: to=<user@example.com>, status=sent"
  }
]
```

### CSV Format

```csv
Timestamp,Queue ID,Recipient,Status
Dec  9 10:15:42,A1B2C3D4E5F,user@example.com,sent
Dec  9 10:15:43,B2C3D4E5F6A,another@domain.org,deferred
```

## Troubleshooting

### Permission Denied

If you get a permission denied error when running the script, make sure:
1. The script is executable: `chmod +x mailcow_delivery_report.py`
2. You have Docker permissions: `sudo usermod -aG docker $USER` (then log out and back in)

### Container Not Found

If the script reports that it cannot find the container:
1. List your running containers: `docker ps`
2. Find the Postfix container name
3. Use the `--container` option with the correct name

### Docker Command Not Found

Make sure Docker is installed and in your PATH. On mailcow servers, Docker should already be installed.

## How It Works

The tool:
1. Retrieves logs from the mailcow Postfix container using `docker logs`
2. Parses the Postfix log entries using regular expressions
3. Extracts delivery information (timestamp, queue ID, recipient, status)
4. Applies any filters specified by the user
5. Formats and displays the results

## License

MIT License - see LICENSE file for details

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Author

Built for mailcow dockerized email server administrators.
