#!/usr/bin/env python3
"""
Main entry point for tvtv2xmltv application
"""
import sys
import argparse
from tvtv2xmltv.config import Config
from tvtv2xmltv.converter import TVTVConverter
from tvtv2xmltv.server import XMLTVServer


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Convert TVTV data to XMLTV format")
    parser.add_argument(
        "--mode",
        choices=["convert", "serve"],
        default="serve",
        help="Mode of operation: convert (one-time) or serve (HTTP server)",
    )
    parser.add_argument("--output", help="Output filename (only for convert mode)")

    args = parser.parse_args()

    config = Config()

    if args.mode == "convert":
        # One-time conversion
        converter = TVTVConverter(config)
        output_file = args.output or config.output_file

        print(f"Converting TVTV data to XMLTV format...")
        print(f"Lineup ID: {config.lineup_id}")
        print(f"Timezone: {config.timezone}")
        print(f"Days: {config.days}")

        try:
            result = converter.save_to_file(output_file)
            print(f"XMLTV file saved to: {result}")
            return 0
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1
    else:
        # Server mode
        print(f"Starting XMLTV server...")
        print(f"Host: {config.host}")
        print(f"Port: {config.port}")
        print(f"Lineup ID: {config.lineup_id}")
        print(f"Timezone: {config.timezone}")
        print(f"Days: {config.days}")
        print(f"Update interval: {config.update_interval} seconds")

        try:
            server = XMLTVServer(config)
            server.run()
            return 0
        except KeyboardInterrupt:
            print("\nShutting down...")
            return 0
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1


if __name__ == "__main__":
    sys.exit(main())
