"""
HTTP server module for serving XMLTV files
"""

import os
import threading
import time
from datetime import datetime, timezone
from flask import Flask, send_file, jsonify
from .converter import TVTVConverter
from .config import Config


class XMLTVServer:
    """HTTP server that serves XMLTV files and auto-updates them"""

    def __init__(self, config=None):
        if config is None:
            config = Config()
        self.config = config
        self.converter = TVTVConverter(config)
        self.app = Flask(__name__)
        self.last_update = None
        self.update_lock = threading.Lock()
        self.update_thread = None
        self.running = False
        self.lineup_files = {}  # Maps lineup_id to filename

        # Register routes
        self._register_routes()

    def _register_routes(self):
        """Register Flask routes"""

        @self.app.route("/")
        def index():
            """Serve the primary XMLTV file or list available lineups"""
            if len(self.config.lineups) == 1:
                # Single lineup mode: serve the default file
                lineup_id = self.config.lineups[0]
                filename = self.lineup_files.get(lineup_id, self.config.output_file)

                if not os.path.exists(filename):
                    return "XMLTV file not yet generated. Please wait...", 503

                return send_file(
                    filename,
                    mimetype="application/xml; charset=utf-8",
                    as_attachment=False,
                )
            else:
                # Multiple lineup mode: return a list of available endpoints
                lineup_list = "\n".join(
                    [f'<li><a href="/{lid}.xml">{lid}.xml</a></li>' for lid in self.config.lineups]
                )
                return (
                    f"""
                <html>
                <head><title>XMLTV Lineups</title></head>
                <body>
                    <h1>Available XMLTV Lineups</h1>
                    <ul>{lineup_list}</ul>
                </body>
                </html>
                """,
                    200,
                )

        @self.app.route("/<lineup_id>.xml")
        def serve_lineup(lineup_id):
            """Serve a specific lineup's XMLTV file"""
            if lineup_id not in self.config.lineups:
                return f"Lineup '{lineup_id}' not configured", 404

            filename = self.lineup_files.get(lineup_id, f"{lineup_id}.xml")

            if not os.path.exists(filename):
                return f"XMLTV file for lineup '{lineup_id}' not yet generated. Please wait...", 503

            return send_file(
                filename,
                mimetype="application/xml; charset=utf-8",
                as_attachment=False,
            )

        @self.app.route("/xmltv.xml")
        def xmltv():
            """Alternative endpoint for XMLTV file (single lineup compatibility)"""
            return index()

        @self.app.route("/health")
        def health():
            """Health check endpoint"""
            files_exist = all(
                os.path.exists(self.lineup_files.get(lid, f"{lid}.xml"))
                for lid in self.config.lineups
            )

            return jsonify(
                {
                    "status": "healthy",
                    "last_update": self.last_update.isoformat() if self.last_update else None,
                    "lineups": self.config.lineups,
                    "files_exist": files_exist,
                }
            )

        @self.app.route("/update")
        def update():
            """Manually trigger an update"""
            self._update_xmltv()
            return jsonify(
                {
                    "status": "updated",
                    "last_update": self.last_update.isoformat() if self.last_update else None,
                    "lineups": self.config.lineups,
                }
            )

    def _update_xmltv(self):
        """Update the XMLTV files for all lineups"""
        with self.update_lock:
            try:
                if len(self.config.lineups) == 1:
                    print(f"Updating XMLTV file: {self.config.output_file}")
                else:
                    print(f"Updating XMLTV files for lineups: {', '.join(self.config.lineups)}")

                saved_files = self.converter.save_to_file()

                # Update the lineup_files mapping
                for i, lineup_id in enumerate(self.config.lineups):
                    self.lineup_files[lineup_id] = saved_files[i]

                self.last_update = datetime.now(timezone.utc)

                if len(saved_files) == 1:
                    print(
                        f"XMLTV file updated successfully at {self.last_update}: "
                        f"{saved_files[0]}"
                    )
                else:
                    print(f"XMLTV files updated successfully at {self.last_update}")
                    for f in saved_files:
                        print(f"  - {f}")
            except Exception as e:  # pylint: disable=broad-except
                print(f"Error updating XMLTV file(s): {e}")

    def _update_loop(self):
        """Background loop that periodically updates the XMLTV file"""
        # Initial update
        self._update_xmltv()

        while self.running:
            time.sleep(self.config.update_interval)
            if self.running:
                self._update_xmltv()

    def start_update_thread(self):
        """Start the background update thread"""
        self.running = True
        self.update_thread = threading.Thread(target=self._update_loop, daemon=True)
        self.update_thread.start()

    def stop_update_thread(self):
        """Stop the background update thread"""
        self.running = False
        if self.update_thread:
            self.update_thread.join(timeout=5)

    def run(self):
        """Run the Flask server"""
        self.start_update_thread()
        try:
            self.app.run(host=self.config.host, port=self.config.port, debug=False)
        finally:
            self.stop_update_thread()
