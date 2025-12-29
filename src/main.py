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

        print("Converting TVTV data to XMLTV format...")
        print(f"Lineups: {', '.join(config.lineups)}")
        print(f"Timezone: {config.timezone}")
        print(f"Days: {config.days}")

        try:
            result_files = converter.save_to_file(output_file)
            if len(result_files) == 1:
                print(f"XMLTV file saved to: {result_files[0]}")
            else:
                print("XMLTV files saved:")
                for f in result_files:
                    print(f"  - {f}")
            return 0
        except Exception as e:  # pylint: disable=broad-except
            print(f"Error: {e}", file=sys.stderr)
            return 1
    else:
        # Server mode
        print("Starting XMLTV server...")
        print(f"Host: {config.host}")
        print(f"Port: {config.port}")
        print(f"Lineups: {', '.join(config.lineups)}")
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
        except Exception as e:  # pylint: disable=broad-except
            print(f"Error: {e}", file=sys.stderr)
            return 1


if __name__ == "__main__":
    sys.exit(main())
