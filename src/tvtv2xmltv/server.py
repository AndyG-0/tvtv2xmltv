"""
HTTP server module for serving XMLTV files
"""

import os
import threading
import time
from datetime import datetime, timezone
from flask import Flask, send_file, jsonify, redirect
from .converter import TVTVConverter
from .config import Config


class XMLTVServer:
    """HTTP server that serves XMLTV files and auto-updates them"""

    # pylint: disable=too-many-instance-attributes

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
        self.runtime_default_lineup = self._load_runtime_default()

        # Register routes
        self._register_routes()

    def _default_lineup_state_path(self):
        """Path to the file that persists a runtime-selected default lineup"""
        out_dir = os.path.dirname(os.path.abspath(self.config.output_file)) or "."
        return os.path.join(out_dir, ".tvtv_default_lineup")

    def _load_runtime_default(self):
        """Load a previously-persisted default lineup selection, if still valid"""
        try:
            with open(self._default_lineup_state_path(), "r", encoding="utf-8") as f:
                lineup_id = f.read().strip()
        except OSError:
            return None

        return lineup_id if lineup_id in self.config.lineups else None

    def _save_runtime_default(self, lineup_id):
        """Persist a runtime-selected default lineup so it survives restarts"""
        with open(self._default_lineup_state_path(), "w", encoding="utf-8") as f:
            f.write(lineup_id)

    def _effective_default_lineup(self):
        """The lineup that should be served at '/', if any (env var wins)"""
        return self.config.default_lineup or self.runtime_default_lineup

    def _serve_lineup_file(self, lineup_id):
        """Serve a single lineup's XMLTV file inline, or a 503 if not yet generated"""
        # Before the first update populates `lineup_files`, guess the filename the
        # converter would use: `output_file` in single-lineup mode, `<id>.xml` in
        # multi-lineup mode (see converter.py's save_to_file()).
        guessed_filename = (
            self.config.output_file if len(self.config.lineups) == 1 else f"{lineup_id}.xml"
        )
        filename = self.lineup_files.get(lineup_id, guessed_filename)

        if not os.path.exists(filename):
            return f"XMLTV file for lineup '{lineup_id}' not yet generated. Please wait...", 503

        return send_file(
            filename,
            mimetype="application/xml; charset=utf-8",
            as_attachment=False,
        )

    def _render_lineup_list(self):
        """Render the HTML listing page of all configured lineups"""
        default_lineup = self._effective_default_lineup()
        rows = []
        for lid in self.config.lineups:
            marker = " (default)" if lid == default_lineup else ""
            stats = self.converter.stats.get(lid)
            if stats:
                ch = stats.get("channels", 0)
                days = stats.get("days", 0)
                progs = stats.get("programs", 0)
                ch_str = f"{ch} channel" if ch == 1 else f"{ch} channels"
                day_str = f"{days} day" if days == 1 else f"{days} days"
                prog_str = f"{progs} program" if progs == 1 else f"{progs} programs"
                stats_info = f" &mdash; <span>{ch_str}, {day_str} of guide ({prog_str})</span>"
            else:
                stats_info = ""

            rows.append(
                f'<li><a href="/{lid}.xml">{lid}.xml</a>{marker}'
                f"{stats_info} "
                f'&mdash; <a href="/set-default/{lid}">set as default</a></li>'
            )
        lineup_list = "\n".join(rows)
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

    def _register_routes(self):
        """Register Flask routes"""

        @self.app.route("/")
        def index():
            """Serve the default XMLTV file, or list available lineups"""
            if len(self.config.lineups) == 1:
                # Single lineup mode: serve the only configured lineup's file
                return self._serve_lineup_file(self.config.lineups[0])

            default_lineup = self._effective_default_lineup()
            if default_lineup:
                return self._serve_lineup_file(default_lineup)

            # No default chosen yet: return a list of available endpoints
            return self._render_lineup_list()

        @self.app.route("/list")
        def list_lineups():
            """Always show the list of configured lineups, regardless of default"""
            return self._render_lineup_list()

        @self.app.route("/set-default/<lineup_id>")
        def set_default(lineup_id):
            """Pick which lineup is served at '/' (persisted across restarts)"""
            if lineup_id not in self.config.lineups:
                return f"Lineup '{lineup_id}' not configured", 404

            self._save_runtime_default(lineup_id)
            self.runtime_default_lineup = lineup_id
            return redirect("/")

        @self.app.route("/<lineup_id>.xml")
        def serve_lineup(lineup_id):
            """Serve a specific lineup's XMLTV file"""
            if lineup_id not in self.config.lineups:
                return f"Lineup '{lineup_id}' not configured", 404

            return self._serve_lineup_file(lineup_id)

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
                    "default_lineup": self._effective_default_lineup(),
                    "files_exist": files_exist,
                    "stats": self.converter.stats,
                }
            )

        @self.app.route("/stats")
        def stats():
            """Feed statistics endpoint"""
            return jsonify(
                {
                    "status": "healthy",
                    "last_update": self.last_update.isoformat() if self.last_update else None,
                    "lineups": self.config.lineups,
                    "stats": self.converter.stats,
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
                    "stats": self.converter.stats,
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
                    lineup_id = self.config.lineups[0]
                    st = self.converter.stats.get(lineup_id, {})
                    ch = st.get("channels", 0)
                    days = st.get("days", 0)
                    progs = st.get("programs", 0)
                    ch_str = f"{ch} channel" if ch == 1 else f"{ch} channels"
                    day_str = f"{days} day" if days == 1 else f"{days} days"
                    prog_str = f"{progs} program" if progs == 1 else f"{progs} programs"
                    print(
                        f"XMLTV file updated successfully at {self.last_update}: "
                        f"{saved_files[0]} ({ch_str}, {day_str} of guide, {prog_str})"
                    )
                else:
                    print(f"XMLTV files updated successfully at {self.last_update}:")
                    for lineup_id in self.config.lineups:
                        filename = self.lineup_files.get(lineup_id, f"{lineup_id}.xml")
                        st = self.converter.stats.get(lineup_id, {})
                        ch = st.get("channels", 0)
                        days = st.get("days", 0)
                        progs = st.get("programs", 0)
                        ch_str = f"{ch} channel" if ch == 1 else f"{ch} channels"
                        day_str = f"{days} day" if days == 1 else f"{days} days"
                        prog_str = f"{progs} program" if progs == 1 else f"{progs} programs"
                        msg = (
                            f"  - {lineup_id} ({filename}): "
                            f"{ch_str}, {day_str} of guide ({prog_str})"
                        )
                        print(msg)
            except Exception as e:  # pylint: disable=broad-except
                print(f"Error updating XMLTV file(s): {e}")

    def _update_loop(self):
        """Background loop that periodically updates the XMLTV file"""
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
        # Fetch fresh feeds before accepting any requests, so "/" and the lineup
        # routes are never stale or missing on first contact.
        self._update_xmltv()
        self.start_update_thread()
        try:
            self.app.run(host=self.config.host, port=self.config.port, debug=False)
        finally:
            self.stop_update_thread()
