"""
HTTP server module for serving XMLTV files
"""

import os
import threading
import time
from datetime import datetime, timezone
from flask import Flask, send_file, jsonify, redirect, request
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
        return os.path.join(out_dir, ".gracenote_default_lineup")

    def _legacy_default_lineup_state_path(self):
        """Legacy path for backward compatibility"""
        out_dir = os.path.dirname(os.path.abspath(self.config.output_file)) or "."
        return os.path.join(out_dir, ".tvtv_default_lineup")

    def _load_runtime_default(self):
        """Load a previously-persisted default lineup selection, if still valid"""
        for path in [self._default_lineup_state_path(), self._legacy_default_lineup_state_path()]:
            try:
                with open(path, "r", encoding="utf-8") as f:
                    lineup_id = f.read().strip()
                if lineup_id in self.config.lineups:
                    return lineup_id
            except OSError:
                continue

        return None

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
        """Render the HTML listing page of all configured lineups and feed statistics"""
        default_lineup = self._effective_default_lineup()
        last_refresh_str = (
            self.last_update.strftime("%Y-%m-%d %H:%M:%S UTC")
            if self.last_update
            else "Not yet refreshed"
        )
        is_refreshed = request.args.get("refreshed") == "1"
        refreshed_alert = ""
        if is_refreshed:
            refreshed_alert = """
            <div class="alert-success">
                <span>&#10003;</span>
                <span>Feeds refreshed successfully!</span>
            </div>
            """

        update_interval_str = (
            f"{self.config.update_interval // 60}m"
            if self.config.update_interval >= 60
            else f"{self.config.update_interval}s"
        )

        cards = []
        for lid in self.config.lineups:
            is_default = lid == default_lineup
            marker = ' <span class="badge badge-default">default</span>' if is_default else ""
            default_action = (
                ""
                if is_default
                else (
                    f'<a href="/set-default/{lid}" '
                    'class="btn btn-outline btn-sm">Set as default</a>'
                )
            )

            stats = self.converter.stats.get(lid, {})
            ch = stats.get("channels", 0)
            days = stats.get("days", 0)
            progs = stats.get("programs", 0)
            date_range = stats.get("date_range") or "N/A"
            file_size = stats.get("file_size_human") or "N/A"
            feed_refreshed = stats.get("last_refreshed") or last_refresh_str

            ch_str = f"{ch} channel" if ch == 1 else f"{ch} channels"
            day_str = f"{days} day" if days == 1 else f"{days} days"
            prog_str = f"{progs} program" if progs == 1 else f"{progs} programs"
            summary_info = f"{ch_str}, {day_str} of guide ({prog_str})"

            cards.append(
                f"""
                <div class="feed-card">
                    <div class="feed-header">
                        <div class="feed-title">
                            <h2><a href="/{lid}.xml">{lid}.xml</a></h2>
                            {marker}
                        </div>
                        <div class="feed-actions">
                            {default_action}
                            <a href="/{lid}.xml" class="btn btn-sm btn-primary" download>
                                Download XML
                            </a>
                        </div>
                    </div>
                    <div class="feed-summary-line">
                        <span>{summary_info}</span>
                    </div>
                    <div class="stats-grid">
                        <div class="stat-box">
                            <div class="stat-label">Channels</div>
                            <div class="stat-value">{ch}</div>
                            <div class="stat-sub">{ch_str}</div>
                        </div>
                        <div class="stat-box">
                            <div class="stat-label">Guide Days</div>
                            <div class="stat-value">{days}</div>
                            <div class="stat-sub">{day_str}</div>
                        </div>
                        <div class="stat-box">
                            <div class="stat-label">Date Range</div>
                            <div class="stat-value stat-dates">{date_range}</div>
                            <div class="stat-sub">Coverage window</div>
                        </div>
                        <div class="stat-box">
                            <div class="stat-label">Programs</div>
                            <div class="stat-value">{progs:,}</div>
                            <div class="stat-sub">Scheduled airings</div>
                        </div>
                        <div class="stat-box">
                            <div class="stat-label">File Size</div>
                            <div class="stat-value">{file_size}</div>
                            <div class="stat-sub">XMLTV payload</div>
                        </div>
                    </div>
                    <div class="feed-footer">
                        <span>Last Refreshed: <strong>{feed_refreshed}</strong></span>
                        <span>Feed URL: <code class="code-inline">/{lid}.xml</code></span>
                    </div>
                </div>
                """
            )

        lineup_cards_html = "\n".join(cards)

        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>XMLTV Lineups &amp; Feed Statistics</title>
    <style>
        :root {{
            --bg: #0f172a;
            --card-bg: #1e293b;
            --card-border: #334155;
            --text: #f8fafc;
            --text-muted: #94a3b8;
            --accent: #38bdf8;
            --accent-green: #34d399;
            --primary: #2563eb;
            --primary-hover: #1d4ed8;
            --badge-bg: #065f46;
            --badge-text: #6ee7b7;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
                Helvetica, Arial, sans-serif;
            background-color: var(--bg);
            color: var(--text);
            line-height: 1.5;
            padding: 2rem 1rem;
        }}
        .container {{
            max-width: 960px;
            margin: 0 auto;
        }}
        header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 1rem;
            margin-bottom: 1.5rem;
            padding-bottom: 1.25rem;
            border-bottom: 1px solid var(--card-border);
        }}
        .header-title h1 {{
            font-size: 1.6rem;
            font-weight: 700;
            color: #fff;
            display: flex;
            align-items: center;
            gap: 0.6rem;
        }}
        .header-actions {{
            display: flex;
            align-items: center;
            gap: 0.75rem;
        }}
        .status-badge {{
            display: inline-flex;
            align-items: center;
            gap: 0.4rem;
            padding: 0.35rem 0.75rem;
            border-radius: 9999px;
            font-size: 0.825rem;
            font-weight: 600;
            background-color: rgba(5, 150, 105, 0.2);
            border: 1px solid rgba(52, 211, 153, 0.4);
            color: var(--badge-text);
        }}
        .status-dot {{
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background-color: var(--accent-green);
        }}
        .btn {{
            display: inline-flex;
            align-items: center;
            gap: 0.4rem;
            background-color: var(--primary);
            color: white;
            padding: 0.5rem 1rem;
            border-radius: 6px;
            text-decoration: none;
            font-weight: 500;
            font-size: 0.875rem;
            border: none;
            cursor: pointer;
            transition: all 0.15s ease;
        }}
        .btn:hover {{ background-color: var(--primary-hover); }}
        .btn:disabled {{ opacity: 0.6; cursor: not-allowed; }}
        .btn-sm {{ padding: 0.35rem 0.7rem; font-size: 0.8rem; }}
        .btn-outline {{
            background-color: transparent;
            border: 1px solid var(--card-border);
            color: var(--text-muted);
        }}
        .btn-outline:hover {{
            background-color: var(--card-border);
            color: var(--text);
        }}
        .alert-success {{
            background-color: rgba(6, 95, 70, 0.5);
            border: 1px solid var(--badge-bg);
            color: #d1fae5;
            padding: 0.75rem 1rem;
            border-radius: 6px;
            margin-bottom: 1.5rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }}
        .server-summary {{
            background-color: var(--card-bg);
            border: 1px solid var(--card-border);
            border-radius: 8px;
            padding: 1.25rem;
            margin-bottom: 1.5rem;
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 1rem;
        }}
        .summary-item .label {{
            font-size: 0.75rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: var(--text-muted);
            margin-bottom: 0.25rem;
        }}
        .summary-item .value {{
            font-size: 1.05rem;
            font-weight: 600;
            color: var(--text);
        }}
        .feed-card {{
            background-color: var(--card-bg);
            border: 1px solid var(--card-border);
            border-radius: 8px;
            padding: 1.25rem 1.5rem;
            margin-bottom: 1.25rem;
        }}
        .feed-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 0.75rem;
            margin-bottom: 0.75rem;
        }}
        .feed-title {{
            display: flex;
            align-items: center;
            gap: 0.6rem;
        }}
        .feed-title h2 {{
            font-size: 1.2rem;
            font-weight: 600;
        }}
        .feed-title a {{
            color: var(--accent);
            text-decoration: none;
        }}
        .feed-title a:hover {{ text-decoration: underline; }}
        .feed-actions {{
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }}
        .feed-summary-line {{
            font-size: 0.875rem;
            color: var(--text-muted);
            margin-bottom: 1rem;
        }}
        .badge {{
            font-size: 0.7rem;
            font-weight: 600;
            padding: 0.15rem 0.5rem;
            border-radius: 4px;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }}
        .badge-default {{
            background-color: var(--badge-bg);
            color: var(--badge-text);
        }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
            gap: 0.75rem;
            margin-bottom: 1rem;
        }}
        .stat-box {{
            background-color: rgba(15, 23, 42, 0.6);
            padding: 0.75rem;
            border-radius: 6px;
            border: 1px solid rgba(51, 65, 85, 0.4);
        }}
        .stat-box .stat-label {{
            font-size: 0.7rem;
            color: var(--text-muted);
            margin-bottom: 0.2rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }}
        .stat-box .stat-value {{
            font-size: 1.05rem;
            font-weight: 700;
            color: var(--text);
        }}
        .stat-box .stat-value.stat-dates {{
            font-size: 0.9rem;
            font-weight: 600;
            word-break: break-word;
        }}
        .stat-box .stat-sub {{
            font-size: 0.75rem;
            color: var(--text-muted);
            margin-top: 0.1rem;
        }}
        .feed-footer {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 0.5rem;
            font-size: 0.8rem;
            color: var(--text-muted);
            padding-top: 0.75rem;
            border-top: 1px solid rgba(51, 65, 85, 0.4);
        }}
        .code-inline {{
            background-color: rgba(15, 23, 42, 0.8);
            padding: 0.15rem 0.4rem;
            border-radius: 4px;
            font-family: monospace;
            color: var(--accent);
        }}
        .instructions {{
            background-color: rgba(30, 41, 59, 0.4);
            border: 1px dashed var(--card-border);
            border-radius: 8px;
            padding: 1.25rem;
            margin-top: 2rem;
        }}
        .instructions h3 {{
            font-size: 0.95rem;
            margin-bottom: 0.5rem;
            color: #fff;
        }}
        .instructions p {{
            font-size: 0.85rem;
            color: var(--text-muted);
            margin-bottom: 0.5rem;
        }}
        .spinner {{
            display: inline-block;
            width: 12px;
            height: 12px;
            border: 2px solid rgba(255,255,255,0.3);
            border-radius: 50%;
            border-top-color: white;
            animation: spin 0.8s linear infinite;
        }}
        @keyframes spin {{ to {{ transform: rotate(360deg); }} }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div class="header-title">
                <h1>Available XMLTV Lineups</h1>
            </div>
            <div class="header-actions">
                <div class="status-badge">
                    <div class="status-dot"></div>
                    <span>Server Healthy</span>
                </div>
                <form id="reload-form" method="POST" action="/update" style="margin:0;">
                    <button type="submit" id="reload-btn" class="btn">
                        <span id="reload-icon">&#128259;</span>
                        <span id="reload-text">Reload Feeds</span>
                    </button>
                </form>
            </div>
        </header>

        {refreshed_alert}

        <div class="server-summary">
            <div class="summary-item">
                <div class="label">Last Refreshed</div>
                <div class="value" id="summary-last-refreshed">{last_refresh_str}</div>
            </div>
            <div class="summary-item">
                <div class="label">Configured Lineups</div>
                <div class="value">{len(self.config.lineups)}</div>
            </div>
            <div class="summary-item">
                <div class="label">Auto-Update Interval</div>
                <div class="value">{update_interval_str}</div>
            </div>
            <div class="summary-item">
                <div class="label">Timezone</div>
                <div class="value">{self.config.timezone}</div>
            </div>
        </div>

        <main>
            {lineup_cards_html}
        </main>

        <section class="instructions">
            <h3>Media Server Integration</h3>
            <p>Add these guide URLs to your media server (Plex, Jellyfin, Emby, Channels DVR):</p>
            <p>Single Lineup / Default:
                <code class="code-inline">
                    http://&lt;your-server&gt;:{self.config.port}/xmltv.xml
                </code>
            </p>
            <p>Specific Lineup:
                <code class="code-inline">
                    http://&lt;your-server&gt;:{self.config.port}/&lt;lineup-id&gt;.xml
                </code>
            </p>
        </section>
    </div>

    <script>
        document.getElementById('reload-form').addEventListener('submit', function(e) {{
            e.preventDefault();
            const btn = document.getElementById('reload-btn');
            const icon = document.getElementById('reload-icon');
            const text = document.getElementById('reload-text');

            btn.disabled = true;
            icon.innerHTML = '<span class="spinner"></span>';
            text.textContent = 'Refreshing...';

            fetch('/update', {{
                method: 'POST',
                headers: {{
                    'Accept': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest'
                }}
            }})
            .then(res => res.json())
            .then(data => {{
                window.location.href = '/list?refreshed=1';
            }})
            .catch(err => {{
                console.error('Error refreshing feeds:', err);
                document.getElementById('reload-form').submit();
            }});
        }});
    </script>
</body>
</html>"""
        return html_content, 200

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
        @self.app.route("/dashboard")
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

        @self.app.route("/update", methods=["GET", "POST"])
        def update():
            """Manually trigger an update"""
            self._update_xmltv()

            accept = request.headers.get("Accept", "")
            format_param = request.args.get("format", "").lower()
            is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"
            wants_json = (
                "application/json" in accept or format_param == "json" or is_ajax or request.is_json
            )

            # If user submitted a form via browser POST without requesting JSON, redirect to /list
            if not wants_json and request.method == "POST":
                return redirect("/list?refreshed=1")

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
                last_refreshed_iso = self.last_update.isoformat()
                for lid in self.config.lineups:
                    if lid in self.converter.stats:
                        self.converter.stats[lid]["last_refreshed"] = last_refreshed_iso

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
