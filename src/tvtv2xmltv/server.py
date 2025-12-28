"""
HTTP server module for serving XMLTV files
"""

import os
import threading
import time
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

        # Register routes
        self._register_routes()

    def _register_routes(self):
        """Register Flask routes"""

        @self.app.route("/")
        def index():
            """Serve the XMLTV file"""
            if not os.path.exists(self.config.output_file):
                return "XMLTV file not yet generated. Please wait...", 503

            return send_file(
                self.config.output_file,
                mimetype="text/xml",
                as_attachment=True,
                download_name=f'xmltv_{time.strftime("%Y%m%d")}.xml',
            )

        @self.app.route("/xmltv.xml")
        def xmltv():
            """Alternative endpoint for XMLTV file"""
            return index()

        @self.app.route("/health")
        def health():
            """Health check endpoint"""
            return jsonify(
                {
                    "status": "healthy",
                    "last_update": self.last_update.isoformat() if self.last_update else None,
                    "file_exists": os.path.exists(self.config.output_file),
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
                }
            )

    def _update_xmltv(self):
        """Update the XMLTV file"""
        with self.update_lock:
            try:
                print(f"Updating XMLTV file: {self.config.output_file}")
                self.converter.save_to_file()
                self.last_update = time.time()
                self.last_update = time.localtime(self.last_update)
                self.last_update = time.strftime("%Y-%m-%d %H:%M:%S", self.last_update)
                from datetime import datetime

                self.last_update = datetime.strptime(self.last_update, "%Y-%m-%d %H:%M:%S")
                print(f"XMLTV file updated successfully at {self.last_update}")
            except Exception as e:
                print(f"Error updating XMLTV file: {e}")

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
