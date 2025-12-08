#!/usr/bin/env python3
"""
HTML Report Generation for TV Show Organizer
Generates detailed HTML reports of the organization process.
"""

from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any


def generate_html_report(
    report_file: Path,
    stats: Dict[str, int],
    processed_shows: List[Dict[str, Any]],
    start_time: datetime,
    end_time: datetime,
    duration: Any,
    dry_run: bool,
    input_dir: Path,
    output_dir: Path,
    log_file: Path
) -> None:
    """
    Generate a pretty HTML report of the execution
    
    Args:
        report_file: Path where the HTML report should be saved
        stats: Dictionary with statistics (shows_processed, seasons_processed, episodes_moved, errors)
        processed_shows: List of processed show details
        start_time: Start time of the operation
        end_time: End time of the operation
        duration: Duration of the operation
        dry_run: Whether this was a dry run
        input_dir: Input directory path
        output_dir: Output directory path
        log_file: Log file path
    """
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TV Show Organizer Report</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #e0e0e0;
            background: #121212;
            padding: 20px;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: #1e1e1e;
            border-radius: 8px;
            box-shadow: 0 2px 20px rgba(0,0,0,0.5);
            padding: 30px;
        }}
        h1 {{
            color: #ffffff;
            border-bottom: 3px solid #5dade2;
            padding-bottom: 10px;
            margin-bottom: 30px;
        }}
        h2 {{
            color: #b0b0b0;
            margin-top: 30px;
            margin-bottom: 15px;
            border-left: 4px solid #5dade2;
            padding-left: 15px;
        }}
        .summary-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }}
        .summary-card {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
            box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
        }}
        .summary-card.error {{
            background: linear-gradient(135deg, #e74c3c 0%, #c0392b 100%);
            box-shadow: 0 4px 15px rgba(231, 76, 60, 0.3);
        }}
        .summary-card.success {{
            background: linear-gradient(135deg, #3498db 0%, #2980b9 100%);
            box-shadow: 0 4px 15px rgba(52, 152, 219, 0.3);
        }}
        .summary-card h3 {{
            font-size: 14px;
            opacity: 0.9;
            margin-bottom: 10px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        .summary-card .value {{
            font-size: 36px;
            font-weight: bold;
        }}
        .info-section {{
            background: #2a2a2a;
            padding: 15px;
            border-radius: 5px;
            margin: 15px 0;
            border: 1px solid #3a3a3a;
        }}
        .info-section p {{
            margin: 5px 0;
            color: #d0d0d0;
        }}
        .info-section strong {{
            color: #ffffff;
        }}
        .info-section code {{
            background: #1a1a1a;
            color: #5dade2;
            padding: 2px 6px;
            border-radius: 3px;
            font-size: 0.9em;
        }}
        .show-card {{
            border: 1px solid #3a3a3a;
            border-radius: 5px;
            margin: 20px 0;
            overflow: hidden;
            background: #252525;
        }}
        .show-header {{
            background: linear-gradient(135deg, #3498db 0%, #2980b9 100%);
            color: white;
            padding: 15px;
            font-weight: bold;
            font-size: 18px;
        }}
        .show-body {{
            padding: 15px;
            background: #252525;
            color: #e0e0e0;
        }}
        .show-body code {{
            background: #1a1a1a;
            color: #5dade2;
            padding: 2px 6px;
            border-radius: 3px;
            font-size: 0.9em;
        }}
        .season-section {{
            margin: 15px 0;
            padding: 10px;
            background: #2a2a2a;
            border-radius: 5px;
            border: 1px solid #3a3a3a;
        }}
        .season-title {{
            font-weight: bold;
            color: #ffffff;
            margin-bottom: 10px;
        }}
        .episode-list {{
            list-style: none;
            margin-left: 20px;
        }}
        .episode-item {{
            padding: 8px;
            margin: 5px 0;
            background: #1e1e1e;
            border-left: 3px solid #5dade2;
            border-radius: 3px;
            color: #e0e0e0;
        }}
        .episode-item.error {{
            border-left-color: #e74c3c;
            background: #2a1a1a;
        }}
        .episode-item.dry-run {{
            border-left-color: #f39c12;
            background: #2a241a;
        }}
        .file-path {{
            font-family: 'Courier New', monospace;
            font-size: 12px;
            color: #888;
            margin-top: 5px;
        }}
        .status-badge {{
            display: inline-block;
            padding: 3px 8px;
            border-radius: 3px;
            font-size: 11px;
            font-weight: bold;
            margin-left: 10px;
        }}
        .status-moved {{
            background: #27ae60;
            color: #ffffff;
        }}
        .status-error {{
            background: #e74c3c;
            color: #ffffff;
        }}
        .status-dry-run {{
            background: #f39c12;
            color: #ffffff;
        }}
        .footer {{
            margin-top: 40px;
            padding-top: 20px;
            border-top: 2px solid #3a3a3a;
            text-align: center;
            color: #888;
            font-size: 14px;
        }}
        .footer code {{
            background: #1a1a1a;
            color: #5dade2;
            padding: 2px 6px;
            border-radius: 3px;
            font-size: 0.9em;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📺 TV Show Organizer Execution Report</h1>
        
        <div class="summary-grid">
            <div class="summary-card success">
                <h3>Shows Processed</h3>
                <div class="value">{stats['shows_processed']}</div>
            </div>
            <div class="summary-card success">
                <h3>Seasons Processed</h3>
                <div class="value">{stats['seasons_processed']}</div>
            </div>
            <div class="summary-card success">
                <h3>Episodes Moved</h3>
                <div class="value">{stats['episodes_moved']}</div>
            </div>
            <div class="summary-card {'error' if stats['errors'] > 0 else 'success'}">
                <h3>Errors</h3>
                <div class="value">{stats['errors']}</div>
            </div>
        </div>
        
        <h2>Execution Information</h2>
        <div class="info-section">
            <p><strong>Start Time:</strong> {start_time.strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p><strong>End Time:</strong> {end_time.strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p><strong>Duration:</strong> {str(duration).split('.')[0]}</p>
            <p><strong>Mode:</strong> {'<span style="color: #f39c12; font-weight: bold;">DRY RUN</span>' if dry_run else '<span style="color: #27ae60; font-weight: bold;">LIVE</span>'}</p>
            <p><strong>Input Directory:</strong> <code>{input_dir}</code></p>
            <p><strong>Output Directory:</strong> <code>{output_dir}</code></p>
            <p><strong>Log File:</strong> <code>{log_file}</code></p>
        </div>
        
        <h2>Processed Shows</h2>
"""
    
    if processed_shows:
        for show in processed_shows:
            html_content += f"""
        <div class="show-card">
            <div class="show-header">
                {show['name']} <span style="font-size: 12px; opacity: 0.9;">({show['folder_type']})</span>
            </div>
            <div class="show-body">
                <p><strong>Original Folder:</strong> <code>{show['original_folder']}</code></p>
"""
            for season in show['seasons']:
                # Use "Specials" for season 0, otherwise "Season {number}"
                if season['season_number'] == 0:
                    season_title = "Specials"
                else:
                    season_title = f"Season {season['season_number']}"
                html_content += f"""
                <div class="season-section">
                    <div class="season-title">{season_title} ({len(season['episodes'])} episodes)</div>
                    <ul class="episode-list">
"""
                for episode in season['episodes']:
                    status_class = episode['status']
                    status_text = episode['status'].replace('_', ' ').title()
                    html_content += f"""
                        <li class="episode-item {status_class}">
                            <strong>{episode['new_file']}</strong>
                            <span class="status-badge status-{episode['status']}">{status_text}</span>
                            <div class="file-path">From: {episode['original_file']}</div>
                            <div class="file-path">To: {episode['new_path']}</div>
"""
                    if episode.get('error'):
                        html_content += f"""
                            <div class="file-path" style="color: #ff6b6b;">Error: {episode['error']}</div>
"""
                    html_content += """
                        </li>
"""
                html_content += """
                    </ul>
                </div>
"""
            html_content += """
            </div>
        </div>
"""
    else:
        html_content += """
        <p style="color: #888; font-style: italic;">No shows were processed.</p>
"""
    
    html_content += f"""
        <div class="footer">
            <p>Generated by TV Show Organizer on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p>Report saved to: <code>{report_file}</code></p>
        </div>
    </div>
</body>
</html>
"""
    
    try:
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
    except Exception as e:
        raise Exception(f"Failed to generate HTML report: {e}")

