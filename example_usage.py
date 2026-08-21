#!/usr/bin/env python3
"""
Example usage of tvtv2xmltv in convert mode with environment variables
"""
import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from tvtv2xmltv.config import Config

# Example: Set environment variables
os.environ["TVTV_LINEUP_ID"] = "30236_OTA"
os.environ["TVTV_TIMEZONE"] = "America/New_York"
os.environ["TVTV_DAYS"] = "2"
os.environ["TVTV_OUTPUT_FILE"] = "example_output.xml"

print("Example: Converting TVTV data to XMLTV format")
print("=" * 50)
print()

# Create configuration
config = Config()
print(f"Configuration:")
print(f"  Lineups: {', '.join(config.lineups)}")
print(f"  Timezone: {config.timezone}")
print(f"  Days: {config.days}")
print(f"  Output File: {config.output_file}")
print()

# Note: This will fail in the example if you don't have network access
# or if the lineup ID is invalid. Replace with a valid lineup ID for your area.
print("Note: This example requires:")
print("  1. Internet connection to reach the Gracenote grid API")
print("  2. A valid lineup ID for your area ({zipCode}_{headendId}, e.g. 85142_OTA)")
print()
print("To run this example successfully:")
print("  1. Update TVTV_LINEUP_ID above to {yourZip}_OTA (or a provider headendId)")
print("  2. Run: uv run python example_usage.py")
print()

# Uncomment to actually run the conversion:
# try:
#     converter = TVTVConverter(config)
#     output_file = converter.save_to_file()
#     print(f"✅ Success! XMLTV file saved to: {output_file}")
# except Exception as e:
#     print(f"❌ Error: {e}")
#     sys.exit(1)

print("(Conversion code commented out - uncomment to run)")

# Uncomment below to run the conversion
# from tvtv2xmltv.converter import TVTVConverter
# try:
#     converter = TVTVConverter(config)
#     output_file = converter.save_to_file()
#     print(f"✅ Success! XMLTV file saved to: {output_file}")
# except Exception as e:
#     print(f"❌ Error: {e}")
#     sys.exit(1)
