#!/usr/bin/env python

import argparse

import signal
import sys

import requests
try:
    from urlparse import urljoin
except ImportError:
    from urllib.parse import urljoin


def signal_handler(signal, frame):
    sys.exit(0)

def get_command_line_arguments():
    parser = argparse.ArgumentParser(description='This is an example program to read RAIN RFID tags using the Impinj Reader API.')
    parser.add_argument('--reader', action='store', dest='reader', required=True, help='The reader supporting the Impinj Reader API. Note that Speedway-based readers will need to include port number 8000, e.g. speedwayr-fa-1a-1a:8000).')
    return parser.parse_args()

def main():
    # Handle Ctrl+C interrupt
    signal.signal(signal.SIGINT, signal_handler)

    arguments = get_command_line_arguments()

    hostname = 'http://{0}'.format(arguments.reader)

    requests.post(urljoin(hostname, 'api/v1/profiles/stop')) # Stop the active preset
    requests.post(urljoin(hostname, 'api/v1/profiles/inventory/presets/default/start')) # Start the default preset
    for event in requests.get(urljoin(hostname, 'api/v1/data/stream'), stream=True).iter_lines(): # Connect to the event stream
        print(event)


if __name__ == "__main__":
    main()
