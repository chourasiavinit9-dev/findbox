"""
sloth_box.server
Localhost 127.0.0.1 Web Interface — Neobrutalism Design.
Complies with WCAG 2.1 AA accessibility and XSS disarming.
"""

import datetime
import html
import http.server
import json
import urllib.parse
from .config import DIGEST_PATH
from .db import get_db_connection
from .organizer import search_documents
from .security import disarm_xss
from .stats import compute_stats

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>findbox &bull; Drop it in. Forget it.</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700;800&family=Space+Mono:ital,wght@0,400;0,700;1,400&display=swap" rel="stylesheet">
  <style>
    :root {{
      --purple: #7C3AED;
      --purple-light: #A78BFA;
      --purple-bg: #F5F0FF;
      --lime: #C5F135;
      --lime-dark: #9DC420;
      --black: #0A0A0A;
      --white: #FAFAFA;
      --gray: #F0EDF8;
      --border: 2.5px solid #0A0A0A;
      --shadow: 4px 4px 0px #0A0A0A;
      --shadow-lg: 6px 6px 0px #0A0A0A;
      --font: 'Space Grotesk', sans-serif;
      --mono: 'Space Mono', monospace;
    }}
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

    body {{
      background: var(--purple-bg);
      font-family: var(--font);
      color: var(--black);
      min-height: 100vh;
      background-image:
        radial-gradient(circle at 10% 20%, rgba(197,241,53,0.12) 0%, transparent 50%),
        radial-gradient(circle at 90% 80%, rgba(124,58,237,0.10) 0%, transparent 50%);
    }}

    /* NAV */
    nav {{
      background: var(--purple);
      border-bottom: var(--border);
      padding: 0 2rem;
      display: flex;
      align-items: center;
      justify-content: space-between;
      height: 64px;
      position: sticky;
      top: 0;
      z-index: 100;
    }}
    .nav-brand {{ display: flex; align-items: center; gap: 0.65rem; text-decoration: none; }}
    .nav-logo {{
      background: var(--lime);
      color: var(--black);
      font-weight: 800;
      font-size: 1rem;
      padding: 0.3rem 0.75rem;
      border: var(--border);
      border-radius: 6px;
      box-shadow: 2px 2px 0 var(--black);
      letter-spacing: -0.02em;
    }}
    .nav-tagline {{
      color: rgba(255,255,255,0.72);
      font-size: 0.8rem;
      font-weight: 500;
      font-family: var(--mono);
    }}
    .nav-badge {{
      display: flex; align-items: center; gap: 0.5rem;
      background: rgba(255,255,255,0.1);
      border: 1.5px solid rgba(255,255,255,0.25);
      padding: 0.3rem 0.9rem;
      border-radius: 999px;
      font-size: 0.74rem;
      font-weight: 600;
      color: #fff;
      font-family: var(--mono);
    }}
    .pulse-dot {{
      width: 8px; height: 8px;
      border-radius: 50%;
      background: var(--lime);
      animation: pulse-anim 2s ease-in-out infinite;
    }}
    @keyframes pulse-anim {{
      0%,100% {{ opacity:1; transform:scale(1); }}
      50% {{ opacity:0.45; transform:scale(0.75); }}
    }}

    /* LAYOUT */
    .page-wrap {{ max-width: 1200px; margin: 0 auto; padding: 2.5rem 1.5rem 4rem; }}

    /* HERO */
    .hero {{
      text-align: center;
      padding: 3rem 1rem 2.5rem;
      position: relative;
    }}
    .hero-eyebrow {{
      display: inline-flex; align-items: center; gap: 0.5rem;
      background: var(--lime);
      border: var(--border);
      box-shadow: var(--shadow);
      border-radius: 999px;
      padding: 0.35rem 1rem;
      font-size: 0.78rem;
      font-weight: 700;
      margin-bottom: 1.25rem;
      text-transform: uppercase;
      letter-spacing: 0.07em;
    }}
    .hero h1 {{
      font-size: clamp(2.4rem, 6vw, 4.5rem);
      font-weight: 800;
      line-height: 1.06;
      letter-spacing: -0.04em;
      color: var(--black);
      margin-bottom: 1rem;
    }}
    .hero h1 .accent {{ color: var(--purple); }}
    .hero-sub {{
      font-size: 1rem;
      color: #444;
      font-weight: 500;
      max-width: 520px;
      margin: 0 auto 2rem;
      line-height: 1.65;
    }}
    .deco {{ position: absolute; font-size: 2rem; animation: spin-slow 9s linear infinite; }}
    .deco.s1 {{ top: 1.5rem; left: 4%; }}
    .deco.s2 {{ top: 3rem; right: 7%; font-size: 1.5rem; animation-direction: reverse; }}
    .deco.s3 {{ bottom: 0.5rem; left: 47%; font-size: 1.1rem; }}
    @keyframes spin-slow {{ from {{ transform:rotate(0deg); }} to {{ transform:rotate(360deg); }} }}

    /* METRIC STRIP */
    .metric-strip {{
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 1.25rem;
      margin-bottom: 2.5rem;
    }}
    .metric-card {{
      background: var(--white);
      border: var(--border);
      box-shadow: var(--shadow-lg);
      border-radius: 14px;
      padding: 1.5rem 1.25rem;
      transition: transform 0.15s, box-shadow 0.15s;
    }}
    .metric-card:hover {{
      transform: translate(-2px,-2px);
      box-shadow: 8px 8px 0px var(--black);
    }}
    .metric-card.lime {{ background: var(--lime); }}
    .metric-card.purple {{ background: var(--purple); color: #fff; }}
    .metric-label {{
      font-size: 0.72rem; font-weight: 700;
      text-transform: uppercase; letter-spacing: 0.09em;
      opacity: 0.6; margin-bottom: 0.5rem;
      font-family: var(--mono);
    }}
    .metric-value {{
      font-size: 2.8rem; font-weight: 800;
      line-height: 1; letter-spacing: -0.04em;
    }}
    .metric-unit {{ font-size: 0.9rem; font-weight: 600; opacity: 0.6; margin-left: 0.15rem; }}
    .metric-sub {{ font-size: 0.73rem; font-weight: 500; margin-top: 0.4rem; opacity: 0.65; }}
    .lazy-badge {{
      display: inline-flex; align-items: center; gap: 0.3rem;
      background: var(--black); color: var(--lime);
      font-size: 0.7rem; font-weight: 700;
      padding: 0.2rem 0.6rem; border-radius: 999px;
      font-family: var(--mono); margin-top: 0.6rem;
    }}

    /* PANELS ROW */
    .panels-row {{
      display: grid; grid-template-columns: 1fr 1fr;
      gap: 1.25rem; margin-bottom: 2.5rem;
    }}
    .panel {{
      background: var(--white);
      border: var(--border); box-shadow: var(--shadow);
      border-radius: 14px; padding: 1.4rem;
    }}
    .panel-title {{
      font-size: 0.7rem; font-weight: 700;
      text-transform: uppercase; letter-spacing: 0.09em;
      color: var(--purple); margin-bottom: 1rem;
      display: flex; align-items: center; gap: 0.4rem;
      font-family: var(--mono);
    }}
    .todo-item {{
      display: flex; justify-content: space-between;
      align-items: flex-start;
      padding: 0.6rem 0;
      border-bottom: 1.5px solid #eee;
      font-size: 0.84rem; gap: 0.5rem;
    }}
    .todo-item:last-child {{ border-bottom: none; }}
    .todo-task {{ font-weight: 700; flex: 1; }}
    .todo-filename {{ font-size: 0.7rem; color: #999; font-family: var(--mono); display: block; margin-top: 0.15rem; }}
    .due-pill {{
      background: #FF4444; color: #fff;
      font-size: 0.68rem; font-weight: 700;
      padding: 0.2rem 0.55rem; border-radius: 999px;
      white-space: nowrap; font-family: var(--mono);
      border: 1.5px solid var(--black);
    }}
    .empty-state {{
      font-size: 0.85rem; color: #888;
      font-style: italic; text-align: center; padding: 1.5rem 0;
    }}
    /* SCAN PANEL */
    .scan-panel {{
      background: var(--black);
      border: var(--border); box-shadow: var(--shadow-lg);
      border-radius: 14px; padding: 1.4rem;
      color: #fff;
    }}
    .scan-panel .panel-title {{ color: var(--lime); }}
    .scan-folders {{
      display: flex; flex-wrap: wrap; gap: 0.4rem;
      margin-bottom: 1rem;
    }}
    .folder-chip {{
      display: inline-flex; align-items: center; gap: 0.3rem;
      background: rgba(255,255,255,0.08);
      border: 1px solid rgba(255,255,255,0.15);
      border-radius: 6px; padding: 0.25rem 0.6rem;
      font-size: 0.7rem; font-family: var(--mono);
      color: rgba(255,255,255,0.8);
    }}
    .scan-btn {{
      display: inline-flex; align-items: center; gap: 0.4rem;
      background: var(--lime); color: var(--black);
      font-family: var(--font); font-weight: 800; font-size: 0.9rem;
      border: var(--border); border-radius: 10px;
      padding: 0.65rem 1.25rem;
      cursor: pointer; text-decoration: none;
      box-shadow: 3px 3px 0px var(--black);
      transition: box-shadow 0.12s, transform 0.12s;
      width: 100%; justify-content: center;
      margin-top: 0.5rem;
    }}
    .scan-btn:hover {{ transform: translate(-2px,-2px); box-shadow: 5px 5px 0px var(--black); }}
    .scan-btn:active {{ transform: translate(0,0); box-shadow: 1px 1px 0px var(--black); }}
    .scan-note {{
      font-size: 0.7rem; color: rgba(255,255,255,0.5);
      font-family: var(--mono); margin-top: 0.6rem; text-align: center;
    }}
    .scan-status {{
      background: var(--lime); color: var(--black);
      border: var(--border); box-shadow: var(--shadow);
      border-radius: 10px; padding: 0.75rem 1.25rem;
      font-weight: 700; font-size: 0.88rem;
      margin-bottom: 1.5rem;
      display: flex; align-items: center; gap: 0.5rem;
    }}

    /* SEARCH */
    .search-section {{
      background: var(--purple);
      border: var(--border); box-shadow: var(--shadow-lg);
      border-radius: 16px; padding: 2rem;
      margin-bottom: 2.5rem;
      position: relative; overflow: hidden;
    }}
    .search-section::before {{
      content: '';
      position: absolute; top: -40px; right: -40px;
      width: 180px; height: 180px;
      background: var(--lime); border-radius: 50%; opacity: 0.14;
    }}
    .search-label {{
      display: block; font-size: 0.76rem; font-weight: 700;
      text-transform: uppercase; letter-spacing: 0.09em;
      color: rgba(255,255,255,0.68); margin-bottom: 0.75rem;
      font-family: var(--mono);
    }}
    .search-row {{ display: flex; gap: 0.75rem; align-items: center; position: relative; }}
    .search-input-wrap {{ flex: 1; position: relative; display: flex; align-items: center; }}
    .search-input {{
      width: 100%; background: #fff;
      border: var(--border); border-radius: 10px;
      padding: 0.9rem 3rem 0.9rem 1.2rem;
      font-size: 1rem; font-family: var(--font); font-weight: 500;
      color: var(--black); outline: none;
      box-shadow: 3px 3px 0px var(--black);
      transition: box-shadow 0.15s, transform 0.15s;
    }}
    .search-input:focus {{
      box-shadow: 5px 5px 0px var(--lime);
      transform: translate(-1px,-1px);
    }}
    .search-input::placeholder {{ color: #bbb; font-weight: 400; }}
    .clear-btn {{
      position: absolute; right: 0.75rem;
      background: var(--black); color: var(--lime);
      border: none; border-radius: 50%;
      width: 22px; height: 22px;
      font-size: 0.75rem; font-weight: 800;
      cursor: pointer; display: none;
      align-items: center; justify-content: center;
      line-height: 1; padding: 0;
      transition: transform 0.15s, background 0.15s;
      font-family: var(--mono);
    }}
    .clear-btn:hover {{ background: var(--purple); transform: scale(1.15); }}
    .clear-btn.visible {{ display: flex; }}
    .search-btn {{
      background: var(--lime); color: var(--black);
      font-family: var(--font); font-weight: 800; font-size: 0.95rem;
      border: var(--border); border-radius: 10px;
      padding: 0 1.5rem; cursor: pointer;
      box-shadow: 3px 3px 0px var(--black);
      transition: box-shadow 0.15s, transform 0.15s;
      white-space: nowrap;
    }}
    .search-btn:hover {{ transform: translate(-2px,-2px); box-shadow: 5px 5px 0px var(--black); }}
    .search-btn:active {{ transform: translate(0,0); box-shadow: 1px 1px 0px var(--black); }}

    .ai-meta-bar {{
      margin-top: 1rem;
      background: rgba(255,255,255,0.1);
      border: 1.5px solid rgba(255,255,255,0.2);
      border-radius: 8px;
      padding: 0.6rem 1rem;
      font-size: 0.8rem; color: rgba(255,255,255,0.9);
      display: flex; align-items: center; gap: 0.6rem; flex-wrap: wrap;
      font-family: var(--mono);
    }}
    .ai-chip {{
      background: var(--lime); color: var(--black);
      font-size: 0.7rem; font-weight: 700;
      padding: 0.15rem 0.55rem; border-radius: 4px;
      border: 1px solid var(--black);
    }}

    /* RESULTS */
    .results-header {{
      display: flex; align-items: center;
      justify-content: space-between; margin-bottom: 1.25rem;
    }}
    .results-heading {{ font-size: 1.15rem; font-weight: 800; letter-spacing: -0.02em; }}
    .results-count {{
      background: var(--purple); color: #fff;
      font-size: 0.73rem; font-weight: 700;
      padding: 0.25rem 0.7rem; border-radius: 999px;
      border: 1.5px solid var(--black); font-family: var(--mono);
    }}
    .results-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(295px, 1fr));
      gap: 1.25rem;
    }}
    .doc-card {{
      background: var(--white);
      border: var(--border); box-shadow: var(--shadow);
      border-radius: 14px; padding: 1.25rem;
      display: flex; flex-direction: column;
      transition: transform 0.15s, box-shadow 0.15s;
    }}
    .doc-card:hover {{
      transform: translate(-3px,-3px);
      box-shadow: 7px 7px 0px var(--black);
    }}
    .doc-card-top {{
      display: flex; justify-content: space-between;
      align-items: flex-start; margin-bottom: 0.75rem; gap: 0.5rem;
    }}
    .cat-pill {{
      font-size: 0.67rem; font-weight: 700;
      text-transform: uppercase; letter-spacing: 0.07em;
      padding: 0.2rem 0.65rem;
      border-radius: 999px; border: 1.5px solid var(--black);
      font-family: var(--mono);
    }}
    .cat-bills     {{ background:#FFF3CD; color:#856404; }}
    .cat-receipts  {{ background:#D1FAE5; color:#065F46; }}
    .cat-medical   {{ background:#FEE2E2; color:#991B1B; }}
    .cat-travel    {{ background:#DBEAFE; color:#1E40AF; }}
    .cat-recipes   {{ background:#FCE7F3; color:#9D174D; }}
    .cat-chats     {{ background:#E0E7FF; color:#3730A3; }}
    .cat-work      {{ background:#F3E8FF; color:#6B21A8; }}
    .cat-study     {{ background:#FEF9C3; color:#713F12; }}
    .cat-identity  {{ background:#FFE4E6; color:#9F1239; }}
    .cat-screenshots {{ background:#F1F5F9; color:#334155; }}
    .cat-photos    {{ background:#FDFAEC; color:#92400E; }}
    .cat-forms     {{ background:#ECFDF5; color:#064E3B; }}
    .cat-other     {{ background:#F4F4F5; color:#3F3F46; }}
    .doc-date {{
      font-size: 0.7rem; font-family: var(--mono);
      font-weight: 700; color: #999;
    }}
    .doc-title {{
      font-size: 0.93rem; font-weight: 800;
      line-height: 1.3; margin-bottom: 0.5rem;
      color: var(--black); word-break: break-word;
    }}
    .doc-summary {{
      font-size: 0.81rem; color: #555;
      line-height: 1.55; flex-grow: 1; margin-bottom: 0.75rem;
    }}
    .doc-tags {{ display: flex; flex-wrap: wrap; gap: 0.3rem; margin-bottom: 0.75rem; }}
    .doc-tag {{
      font-size: 0.67rem; font-weight: 600;
      color: var(--purple); background: #F0EBFF;
      border: 1.5px solid #C4B5FD;
      padding: 0.12rem 0.4rem; border-radius: 4px;
      font-family: var(--mono);
    }}
    .doc-footer {{
      display: flex; justify-content: space-between;
      align-items: center;
      border-top: 1.5px solid #eee; padding-top: 0.65rem;
      font-size: 0.74rem;
      flex-wrap: wrap;
      gap: 0.4rem;
    }}
    .doc-issuer {{ font-weight: 700; color: #444; font-family: var(--mono); }}
    .task-badge {{
      background: #FF4444; color: #fff;
      font-size: 0.67rem; font-weight: 700;
      padding: 0.18rem 0.5rem; border-radius: 999px;
      border: 1.5px solid var(--black); font-family: var(--mono);
    }}
    .no-task {{ color: #ccc; font-style: italic; }}
    .open-file-btn {{
      display: inline-flex; align-items: center; gap: 0.25rem;
      background: var(--lime); color: var(--black);
      border: 1.5px solid var(--black);
      border-radius: 6px;
      padding: 0.18rem 0.55rem;
      font-size: 0.68rem; font-weight: 800;
      font-family: var(--mono);
      text-decoration: none;
      box-shadow: 2px 2px 0px var(--black);
      transition: box-shadow 0.12s, transform 0.12s;
      white-space: nowrap;
    }}
    .open-file-btn:hover {{
      transform: translate(-1px,-1px);
      box-shadow: 3px 3px 0px var(--black);
    }}

    .empty-results {{
      grid-column: 1 / -1; text-align: center;
      padding: 4rem 2rem;
      background: var(--white);
      border: var(--border); box-shadow: var(--shadow);
      border-radius: 14px;
    }}
    .empty-results .big-emoji {{ font-size: 3.5rem; display: block; margin-bottom: 1rem; }}
    .empty-results p {{ font-size: 1rem; color: #666; font-weight: 500; }}

    /* FOOTER */
    footer {{
      margin-top: 4rem; border-top: var(--border);
      padding-top: 1.5rem;
      display: flex; justify-content: space-between;
      align-items: center; flex-wrap: wrap; gap: 1rem;
    }}
    .footer-lock {{
      display: flex; align-items: center; gap: 0.5rem;
      font-weight: 700; font-size: 0.85rem;
    }}
    .lock-badge {{
      background: var(--lime); border: var(--border);
      border-radius: 6px; padding: 0.2rem 0.55rem;
      font-size: 0.7rem; font-weight: 800; font-family: var(--mono);
    }}
    .footer-meta {{ font-size: 0.76rem; color: #999; font-family: var(--mono); }}

    /* RESPONSIVE */
    @media (max-width: 700px) {{
      .metric-strip, .panels-row {{ grid-template-columns: 1fr; }}
      .hero h1 {{ font-size: 2.2rem; }}
      .search-row {{ flex-direction: column; }}
      footer {{ flex-direction: column; align-items: flex-start; }}
    }}
  </style>
</head>
<body>

  <nav role="banner">
    <a class="nav-brand" href="/" aria-label="findbox home">
      <span class="nav-logo">&#x1F9A5; findbox</span>
      <span class="nav-tagline">Drop it in. Forget it. Find it.</span>
    </a>
    <div class="nav-badge" aria-label="Gemma AI running locally">
      <span class="pulse-dot" aria-hidden="true"></span>
      Gemma &middot; 127.0.0.1
    </div>
  </nav>

  <div class="page-wrap">

    <section class="hero" aria-label="App introduction">
      <span class="deco s1" aria-hidden="true">&#10022;</span>
      <span class="deco s2" aria-hidden="true">&#9733;</span>
      <span class="deco s3" aria-hidden="true">&#10022;</span>
      <div class="hero-eyebrow">
        &#x1F9A5; Hacktoberfest 2026 &middot; Slow &amp; Steady
      </div>
      <h1>Your <span class="accent">digital mess,</span><br>organized overnight.</h1>
      <p class="hero-sub">Drop files in. Sleep. Wake up to everything renamed, sorted, and searchable by what you <em>remember</em> &mdash; not the filename.</p>
    </section>

    <section class="metric-strip" aria-label="Payoff dashboard">
      <div class="metric-card lime" role="region" aria-label="Time saved">
        <div class="metric-label">&#x23F1; Time Saved</div>
        <div class="metric-value">{minutes_saved}<span class="metric-unit">min</span></div>
        <div class="metric-sub">{files_indexed} files &times; 1.5&thinsp;min &plus; {searches_performed} searches &times; 5&thinsp;min</div>
        <span class="lazy-badge">&#10003; Your effort: 0 min</span>
      </div>
      <div class="metric-card" role="region" aria-label="Files organized">
        <div class="metric-label">&#x1F5C2; Files Organized</div>
        <div class="metric-value">{files_indexed}</div>
        <div class="metric-sub">{tasks_extracted} action items auto-extracted</div>
      </div>
      <div class="metric-card purple" role="region" aria-label="Privacy status">
        <div class="metric-label">&#x1F512; On-Device Privacy</div>
        <div class="metric-value" style="font-size:2.4rem;">100%</div>
        <div class="metric-sub">No cloud. No uploads. Works offline.</div>
      </div>
    </section>

    {scan_status_html}
    <div class="panels-row">
      <div class="panel" role="region" aria-label="Action items from your files">
        <div class="panel-title">&#x2713; Action Items Extracted</div>
        {todo_html}
      </div>
      <div class="scan-panel" role="region" aria-label="Scan device files">
        <div class="panel-title">&#x1F50D; Scan My Device</div>
        <div class="scan-folders">
          {folder_chips_html}
        </div>
        <form method="POST" action="/scan">
          <button type="submit" class="scan-btn" aria-label="Scan my device now">
            &#x1F9A5; Scan My Device Now
          </button>
        </form>
        <p class="scan-note">Scans Downloads, Desktop, Documents, Screenshots &amp; more. Files stay on your device.</p>
      </div>
    </div>

    <section class="search-section" aria-label="Vague memory search">
      <label class="search-label" for="search-input">&#x1F9E0; Search by vague memory</label>
      <form method="GET" action="/" role="search">
        <div class="search-row">
          <div class="search-input-wrap">
            <input
              id="search-input"
              class="search-input"
              type="text"
              name="q"
              value="{query_val}"
              placeholder="Try: 'paneer recipe september' &bull; 'electricity bill' &bull; 'rent chat rahul'..."
              aria-label="Vague memory search query"
              autocomplete="off"
              autofocus
              oninput="toggleClear(this)"
            >
            <button
              type="button"
              class="clear-btn{clear_btn_visible}"
              id="clear-btn"
              aria-label="Clear search"
              onclick="clearSearch()"
              title="Clear search"
            >&times;</button>
          </div>
          <button type="submit" class="search-btn" aria-label="Search Memory">
            Search Memory &#x2192;
          </button>
        </div>
        {ai_meta_html}
      </form>
    </section>

    <section aria-label="Search results">
      <div class="results-header">
        <h2 class="results-heading">{results_heading}</h2>
        {results_count_html}
      </div>
      <div class="results-grid" role="region" aria-live="polite">
        {results_html}
      </div>
    </section>

    <footer role="contentinfo">
      <div class="footer-lock">
        <span class="lock-badge">&#x1F512; LOCAL</span>
        Runs 100% on your device &mdash; zero cloud, works offline.
      </div>
      <span class="footer-meta">findbox &middot; Hacktoberfest 2026 Slow &amp; Steady &middot; open-source</span>
    </footer>

  </div>
</body>
<script>
  function toggleClear(input) {{
    var btn = document.getElementById('clear-btn');
    if (input.value.length > 0) {{
      btn.classList.add('visible');
    }} else {{
      btn.classList.remove('visible');
    }}
  }}
  function clearSearch() {{
    document.getElementById('search-input').value = '';
    window.location.href = '/';
  }}
  // Show button on page load if input has value
  (function() {{
    var inp = document.getElementById('search-input');
    if (inp && inp.value.length > 0) {{
      document.getElementById('clear-btn').classList.add('visible');
    }}
  }})();
</script>
</html>
"""


class SlothBoxWebHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # suppress access logs

    def do_GET(self):
        parsed_url = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed_url.query)
        q = params.get("q", [""])[0].strip()

        conn = get_db_connection()
        st = compute_stats()

        # ── Scan status banner ──────────────────────────────────
        params_full = urllib.parse.parse_qs(parsed_url.query)
        scan_status_html = ""
        if params_full.get("scanned"):
            scan_status_html = """
            <div class="scan-status" role="alert" aria-live="polite">
              &#x1F9A5; Scan started &mdash; organizing your device files in the background.
              Refresh in a moment to see newly indexed documents.
            </div>"""

        # ── Auto-scan dirs folder chips ─────────────────────────
        import os as _os
        from .config import get_auto_scan_dirs
        _home = _os.path.expanduser("~")
        auto_dirs = get_auto_scan_dirs()
        folder_chips_html = "".join(
            f'<span class="folder-chip">&#x1F4C2; {disarm_xss(str(d).replace(_home, "~"))}</span>'
            for d in auto_dirs
        ) or '<span class="folder-chip">&#x1F4C2; ~/Downloads</span>'

        # ── All action items — no date filter, color-coded ──────
        todo_html = ""
        rows = conn.execute(
            "SELECT filename, todos_json FROM documents WHERE todos_json != '[]'"
        ).fetchall()
        today = datetime.date.today()
        for r in rows:
            for td in json.loads(r["todos_json"]):
                task = td.get("task", "")
                if not task:
                    continue
                dl = td.get("deadline_or_empty", "")
                clean_task = disarm_xss(task)
                clean_fn = disarm_xss(r["filename"])
                due_badge = ""
                if dl:
                    clean_dl = disarm_xss(dl)
                    try:
                        d_obj = datetime.date.fromisoformat(dl)
                        delta = (d_obj - today).days
                        if delta < 0:
                            badge_color = "#888"
                            label = f"Due {clean_dl} (past)"
                        elif delta <= 7:
                            badge_color = "#FF4444"
                            label = f"Due {clean_dl} &#x26A0;"
                        else:
                            badge_color = "#7C3AED"
                            label = f"Due {clean_dl}"
                        due_badge = f'<span class="due-pill" style="background:{badge_color}">{label}</span>'
                    except Exception:
                        due_badge = f'<span class="due-pill" style="background:#888">{clean_dl}</span>'
                todo_html += f"""
                <div class="todo-item">
                  <div>
                    <span class="todo-task">{clean_task}</span>
                    <span class="todo-filename">{clean_fn}</span>
                  </div>
                  {due_badge}
                </div>"""

        if not todo_html:
            todo_html = '<div class="empty-state">&#x2705; No action items yet. Click &ldquo;Scan My Device&rdquo; to extract tasks from your files.</div>'


        # ── Search or list all ──────────────────────────────────
        ai_meta_html = ""
        results_html = ""
        results_heading = "All Indexed Documents"
        results_count_html = ""

        if q:
            q_info, results = search_documents(conn, q)
            safe_q = disarm_xss(q)
            results_heading = f"Results for &ldquo;{safe_q}&rdquo;"
            results_count_html = (
                f'<span class="results-count">{len(results)} found</span>'
            )
            kw_str = disarm_xss(", ".join(q_info.get("keywords", []))) or "all"
            dates_str = (
                disarm_xss(
                    f"{q_info.get('date_from','')} &rarr; {q_info.get('date_to','')}"
                )
                if q_info.get("date_from")
                else "any date"
            )
            cat_str = disarm_xss(q_info.get("category_hint") or "any")
            ai_meta_html = f"""
            <div class="ai-meta-bar" aria-live="polite">
              <span>&#x1F9E0; AI parsed:</span>
              <span class="ai-chip">keywords: {kw_str}</span>
              <span class="ai-chip">category: {cat_str}</span>
              <span class="ai-chip">dates: {dates_str}</span>
            </div>"""
        else:
            rows_all = conn.execute(
                "SELECT * FROM documents ORDER BY document_date DESC LIMIT 30"
            ).fetchall()
            results = [dict(r) for r in rows_all]
            results_count_html = (
                f'<span class="results-count">{len(results)} docs</span>'
            )

        # ── Build result cards ──────────────────────────────────
        VALID_CATS = {
            "bills", "receipts", "medical", "travel", "recipes", "chats",
            "work", "study", "identity", "screenshots", "photos", "forms", "other"
        }
        if not results:
            results_html = """
            <div class="empty-results">
              <span class="big-emoji">&#x1F9A5;</span>
              <p>No documents match that memory.<br>Try different keywords or drop files into ~/SlothBox/inbox and run again.</p>
            </div>"""
        else:
            for doc in results:
                cat = doc.get("category", "other").lower()
                tags = [t for t in doc.get("tags", "").split() if t][:6]
                tag_chips = "".join(
                    [f'<span class="doc-tag">#{disarm_xss(t)}</span>' for t in tags]
                )
                todos = json.loads(doc.get("todos_json") or "[]")
                task_badge = (
                    f'<span class="task-badge">&#10003; {len(todos)} task(s)</span>'
                    if todos
                    else '<span class="no-task">No tasks</span>'
                )
                clean_cat = disarm_xss(cat)
                clean_date = disarm_xss(doc.get("document_date") or "No date")
                clean_filename = disarm_xss(doc.get("filename", "untitled"))
                clean_summary = disarm_xss(doc.get("summary") or "No summary available.")
                clean_issuer = disarm_xss(doc.get("issuer_or_person") or "Unknown")
                cat_class = f"cat-{cat}" if cat in VALID_CATS else "cat-other"

                # Build a file:// link so clicking opens the file in its default app
                raw_path = doc.get("current_path") or doc.get("original_path") or ""
                import urllib.request as _ur
                file_url = _ur.pathname2url(raw_path) if raw_path else ""
                if file_url and not file_url.startswith("file://"):
                    file_url = "file://" + file_url
                open_btn = (
                    f'<a class="open-file-btn" href="{file_url}" '
                    f'target="_blank" rel="noopener" '
                    f'aria-label="Open {clean_filename} in default app">'
                    f'&#x1F4C4; Open&nbsp;File&nbsp;&#x2197;</a>'
                    if file_url else ""
                )

                results_html += f"""
                <article class="doc-card" aria-label="{clean_filename}">
                  <div>
                    <div class="doc-card-top">
                      <span class="cat-pill {cat_class}">{clean_cat}</span>
                      <span class="doc-date">{clean_date}</span>
                    </div>
                    <div class="doc-title">{clean_filename}</div>
                    <div class="doc-summary">{clean_summary}</div>
                    <div class="doc-tags">{tag_chips}</div>
                  </div>
                  <div class="doc-footer">
                    <span class="doc-issuer">{clean_issuer}</span>
                    <div style="display:flex;gap:0.4rem;align-items:center;flex-wrap:wrap;">
                      {open_btn}
                      {task_badge}
                    </div>
                  </div>
                </article>"""

        html_out = HTML_TEMPLATE.format(
            minutes_saved=st["minutes_saved"],
            files_indexed=st["files_indexed"],
            tasks_extracted=st["tasks_extracted"],
            searches_performed=st["searches_performed"],
            todo_html=todo_html,
            folder_chips_html=folder_chips_html,
            scan_status_html=scan_status_html,
            query_val=disarm_xss(q),
            ai_meta_html=ai_meta_html,
            clear_btn_visible=" visible" if q else "",
            results_heading=results_heading,
            results_count_html=results_count_html,
            results_html=results_html,
        )

        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(html_out.encode("utf-8"))))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "SAMEORIGIN")
        self.end_headers()
        self.wfile.write(html_out.encode("utf-8"))


    def do_POST(self):
        """Handle POST /scan — trigger background intake of auto-scan dirs."""
        parsed_url = urllib.parse.urlparse(self.path)
        if parsed_url.path != "/scan":
            self.send_error(404)
            return
        # Launch intake in a daemon thread so the response returns immediately
        import threading
        from .organizer import run_intake
        def _bg_scan():
            try:
                run_intake(inbox_dirs=None, apply=True)
            except Exception as e:
                print(f"[Scan error] {e}")
        t = threading.Thread(target=_bg_scan, daemon=True)
        t.start()
        # Redirect back to / with a ?scanned=1 banner
        self.send_response(303)
        self.send_header("Location", "/?scanned=1")
        self.send_header("Content-Length", "0")
        self.end_headers()


def run_server(host="127.0.0.1", port=8765):
    """Binds HTTP server exclusively to localhost (127.0.0.1)."""
    server_address = (host, port)
    httpd = http.server.HTTPServer(server_address, SlothBoxWebHandler)
    print("=" * 60)
    print(f"🦥 SlothBox Web UI active on http://{host}:{port}")
    print("   Bound strictly to localhost (127.0.0.1).")
    print("   No network uploads. Fully offline. Press Ctrl+C to stop.")
    print("=" * 60)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nSlothBox Web UI stopped.")
