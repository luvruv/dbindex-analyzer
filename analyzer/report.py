"""Report generation module for DbIndex Analyzer.

Generates:
1. Executive SQL migration script (`recommendations.sql`) with both CREATE INDEX and safe DROP INDEX commands.
2. Production-grade interactive HTML dashboard (`report.html`) featuring schema metrics, missing indexes,
   redundant index detection, healthy index catalogs, and one-click copyable SQL migration scripts.
"""

import html
from datetime import datetime
from typing import List, Optional, Any


def write_sql_file(suggestions: List[Any], path: str, redundant: Optional[List[Any]] = None):
    """Write complete migration SQL statements (both CREATE and DROP) to a script file.

    Parameters:
    -----------
    suggestions : list
        List of missing index suggestions (CREATE INDEX).
    path : str
        Target file path.
    redundant : list, optional
        List of redundant/unnecessary indexes (DROP INDEX).
    """
    with open(path, "w", encoding="utf-8") as f:
        f.write("-- =============================================================================\n")
        f.write("-- DbIndex Analyzer - Production Database Optimization Script\n")
        f.write(f"-- Generated: {datetime.now():%Y-%m-%d %H:%M:%S}\n")
        f.write("-- =============================================================================\n\n")

        # Section 1: Missing Indexes
        f.write("-- =============================================================================\n")
        f.write("-- PART 1: MISSING INDEXES (CREATE TO ACCELERATE READ PERFORMANCE)\n")
        f.write("-- =============================================================================\n\n")

        if suggestions:
            for s in suggestions:
                severity = getattr(s, "severity", "RECOMMENDED")
                f.write(f"-- [{severity}] {s.table}.{s.column}\n")
                f.write(f"-- Why: {s.reason}\n")
                f.write(f"-- Expected Speedup: {s.speedup}\n")
                f.write(f"{s.sql}\n\n")
        else:
            f.write("-- No missing indexes detected. All critical columns appear to be indexed.\n\n")

        # Section 2: Redundant / Wasteful Indexes to Drop
        if redundant:
            f.write("\n-- =============================================================================\n")
            f.write("-- PART 2: REDUNDANT & UNNECESSARY INDEXES (DROP TO SAVE STORAGE & WRITE I/O)\n")
            f.write("-- =============================================================================\n\n")
            for r in redundant:
                cols = ", ".join(r.columns)
                f.write(f"-- [REDUNDANT: {r.issue_type}] Table: {r.table} | Index: {r.index_name} ({cols})\n")
                f.write(f"-- Reason: {r.reason}\n")
                f.write(f"-- Impact: {r.impact}\n")
                f.write(f"{r.sql}\n\n")


def write_html_report(
    db_name: str,
    table_count: int,
    column_count: int,
    suggestions: List[Any],
    path: str,
    redundant: Optional[List[Any]] = None,
    healthy: Optional[List[Any]] = None,
    metrics: Optional[Any] = None,
    metadata: Optional[Any] = None,
    engine_type: str = "postgresql",
):
    """Generate a production-grade executive dashboard HTML report."""
    esc = html.escape
    redundant = redundant or []
    healthy = healthy or []

    # Score and Grade
    score = getattr(metrics, "health_score", 85)
    grade = getattr(metrics, "health_grade", "B")
    total_existing = getattr(metrics, "total_existing_indexes", len(healthy) + len(redundant))
    pk_cov = getattr(metrics, "pk_coverage_pct", 100.0)
    fk_cov = getattr(metrics, "fk_coverage_pct", 100.0)
    insights = getattr(metrics, "insights", [])

    # Color mapping for health grade
    grade_colors = {
        "A": "#10b981",  # emerald green
        "B": "#3b82f6",  # blue
        "C": "#f59e0b",  # amber
        "D": "#ef4444",  # red
        "F": "#b91c1c",  # dark red
    }
    score_color = grade_colors.get(grade, "#3b82f6")

    # Generate SQL batches for copy areas
    create_sql = "\n".join(s.sql for s in suggestions) if suggestions else "-- No missing indexes required."
    drop_sql = "\n".join(r.sql for r in redundant) if redundant else "-- No redundant indexes found."
    combined_sql = f"-- 1. CREATE MISSING INDEXES\n{create_sql}\n\n-- 2. DROP REDUNDANT INDEXES\n{drop_sql}"

    # Missing Indexes Rows
    missing_rows = []
    for s in suggestions:
        sev = getattr(s, "severity", "MEDIUM")
        sev_color = "#ef4444" if sev == "CRITICAL" else "#f59e0b" if sev == "HIGH" else "#3b82f6"
        missing_rows.append(
            f"""<tr data-table="{esc(s.table.lower())}" data-severity="{esc(sev)}">
                <td><b>{esc(s.table)}</b>.{esc(s.column)}</td>
                <td><span class="badge" style="background:{sev_color}20; color:{sev_color}; border:1px solid {sev_color}40;">{esc(sev)}</span></td>
                <td>{esc(s.reason)}</td>
                <td><span class="speedup-tag">⚡ {esc(s.speedup)}</span></td>
                <td>
                    <div class="sql-cell">
                        <code>{esc(s.sql)}</code>
                        <button class="btn-copy-sm" onclick="copySnippet('{esc(s.sql)}')">Copy</button>
                    </div>
                </td>
            </tr>"""
        )

    # Redundant Indexes Rows
    redundant_rows = []
    for r in redundant:
        redundant_rows.append(
            f"""<tr data-table="{esc(r.table.lower())}">
                <td><b>{esc(r.table)}</b></td>
                <td><code class="idx-name">{esc(r.index_name)}</code><div class="sub-col">({esc(", ".join(r.columns))})</div></td>
                <td><span class="badge badge-drop">{esc(r.issue_type)}</span></td>
                <td>
                    <div style="font-weight:500; margin-bottom:4px;">{esc(r.reason)}</div>
                    <div style="font-size:12px; color:#64748b;">{esc(r.impact)}</div>
                </td>
                <td>
                    <div class="sql-cell">
                        <code class="sql-drop">{esc(r.sql)}</code>
                        <button class="btn-copy-sm" onclick="copySnippet('{esc(r.sql)}')">Copy</button>
                    </div>
                </td>
            </tr>"""
        )

    # Healthy Indexes Rows
    healthy_rows = []
    for h in healthy:
        cat_badge = "#10b981" if h.category == "PRIMARY_KEY" else "#6366f1" if h.category == "UNIQUE_CONSTRAINT" else "#0ea5e9"
        healthy_rows.append(
            f"""<tr data-table="{esc(h.table.lower())}">
                <td><b>{esc(h.table)}</b></td>
                <td><code>{esc(h.index_name)}</code></td>
                <td>{esc(", ".join(h.columns))}</td>
                <td><span class="badge" style="background:{cat_badge}20; color:{cat_badge}; border:1px solid {cat_badge}40;">{esc(h.category)}</span></td>
                <td style="font-size:13px; color:#475569;">{esc(h.description)}</td>
            </tr>"""
        )

    # Schema Knowledge Catalog Rows
    schema_rows = []
    if metadata and hasattr(metadata, "tables"):
        for tname, tschema in sorted(metadata.tables.items()):
            col_list = ", ".join(f"{c.name} ({c.data_type})" for c in tschema.columns)
            pk_str = ", ".join(tschema.primary_key) if tschema.primary_key else "None"
            pk_badge = '<span class="badge" style="background:#10b98120; color:#10b981;">Defined</span>' if tschema.primary_key else '<span class="badge" style="background:#ef444420; color:#ef4444;">Missing PK</span>'
            fk_count = len(tschema.foreign_keys)
            idx_count = len(tschema.indexes)
            schema_rows.append(
                f"""<tr data-table="{esc(tname.lower())}">
                    <td><b>{esc(tname)}</b></td>
                    <td>{len(tschema.columns)} cols</td>
                    <td>{pk_badge} <code>{esc(pk_str)}</code></td>
                    <td>{fk_count} relationship(s)</td>
                    <td>{idx_count} index(es)</td>
                    <td style="font-size:12px; color:#64748b;">{esc(col_list[:120])}{"..." if len(col_list) > 120 else ""}</td>
                </tr>"""
            )

    insights_html = "".join(f'<li class="insight-item">{esc(i)}</li>' for i in insights)

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>DbIndex Analyzer - Production Health Dashboard: {esc(db_name)}</title>
<style>
:root {{
    --primary: #2563eb;
    --primary-dark: #1d4ed8;
    --bg: #0f172a;
    --surface: #1e293b;
    --surface-card: #ffffff;
    --text-main: #0f172a;
    --text-muted: #64748b;
    --border: #e2e8f0;
    --success: #10b981;
    --warning: #f59e0b;
    --danger: #ef4444;
}}
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    background: #f8fafc;
    color: var(--text-main);
    line-height: 1.5;
    padding-bottom: 60px;
}}
header {{
    background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
    color: #ffffff;
    padding: 32px 40px;
    box-shadow: 0 4px 20px rgba(0,0,0,0.15);
}}
.header-top {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: 16px;
}}
.header-brand h1 {{
    font-size: 26px;
    font-weight: 700;
    letter-spacing: -0.5px;
    display: flex;
    align-items: center;
    gap: 12px;
}}
.header-badge {{
    background: rgba(37,99,235,0.25);
    color: #93c5fd;
    border: 1px solid rgba(147,197,253,0.3);
    font-size: 12px;
    padding: 4px 10px;
    border-radius: 9999px;
    font-weight: 600;
    text-transform: uppercase;
}}
.header-meta {{
    font-size: 14px;
    color: #94a3b8;
    margin-top: 8px;
}}
.header-meta b {{ color: #f8fafc; }}

.container {{
    max-width: 1300px;
    margin: -24px auto 0;
    padding: 0 24px;
}}

/* Score & Stats Grid */
.metrics-grid {{
    display: grid;
    grid-template-columns: 280px repeat(auto-fit, minmax(180px, 1fr));
    gap: 16px;
    margin-bottom: 24px;
}}
.card {{
    background: var(--surface-card);
    border-radius: 12px;
    padding: 20px 24px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.05), 0 10px 15px -3px rgba(0,0,0,0.05);
    border: 1px solid var(--border);
}}
.score-card {{
    background: linear-gradient(135deg, #ffffff 0%, #f1f5f9 100%);
    display: flex;
    align-items: center;
    gap: 20px;
    border-left: 6px solid {score_color};
}}
.score-circle {{
    width: 72px;
    height: 72px;
    border-radius: 50%;
    background: {score_color}15;
    border: 3px solid {score_color};
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
}}
.score-val {{ font-size: 26px; font-weight: 800; color: {score_color}; line-height: 1; }}
.score-grade {{ font-size: 11px; font-weight: 700; color: {score_color}; text-transform: uppercase; }}
.stat-title {{ font-size: 12px; text-transform: uppercase; color: var(--text-muted); font-weight: 600; }}
.stat-num {{ font-size: 28px; font-weight: 700; color: #0f172a; margin-top: 4px; }}
.stat-sub {{ font-size: 12px; color: var(--text-muted); margin-top: 2px; }}

/* Insights Box */
.insights-box {{
    background: #ffffff;
    border-radius: 12px;
    padding: 20px 24px;
    margin-bottom: 24px;
    border: 1px solid var(--border);
    box-shadow: 0 1px 3px rgba(0,0,0,0.05);
}}
.insights-box h3 {{
    font-size: 16px;
    font-weight: 700;
    color: #1e293b;
    margin-bottom: 12px;
    display: flex;
    align-items: center;
    gap: 8px;
}}
.insight-item {{
    margin-bottom: 8px;
    font-size: 14px;
    color: #334155;
    list-style: none;
}}

/* Interactive Tabs */
.tabs-header {{
    display: flex;
    gap: 8px;
    border-bottom: 2px solid var(--border);
    margin-bottom: 20px;
    overflow-x: auto;
}}
.tab-btn {{
    padding: 12px 20px;
    background: transparent;
    border: none;
    font-size: 15px;
    font-weight: 600;
    color: var(--text-muted);
    cursor: pointer;
    border-bottom: 3px solid transparent;
    margin-bottom: -2px;
    transition: all 0.2s;
    display: flex;
    align-items: center;
    gap: 8px;
}}
.tab-btn:hover {{ color: var(--primary); }}
.tab-btn.active {{
    color: var(--primary);
    border-bottom-color: var(--primary);
}}
.pill-count {{
    background: #e2e8f0;
    color: #475569;
    font-size: 11px;
    padding: 2px 8px;
    border-radius: 9999px;
    font-weight: 700;
}}
.tab-btn.active .pill-count {{
    background: var(--primary);
    color: #ffffff;
}}

/* Filter Bar */
.filter-bar {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 16px;
    margin-bottom: 16px;
    flex-wrap: wrap;
}}
.search-input {{
    padding: 10px 16px;
    border: 1px solid var(--border);
    border-radius: 8px;
    font-size: 14px;
    width: 320px;
    background: #ffffff;
}}
.search-input:focus {{ outline: 2px solid var(--primary); }}

/* Tables */
.table-container {{
    background: #ffffff;
    border-radius: 12px;
    border: 1px solid var(--border);
    overflow: hidden;
    box-shadow: 0 1px 3px rgba(0,0,0,0.05);
}}
table {{
    width: 100%;
    border-collapse: collapse;
    text-align: left;
    font-size: 14px;
}}
th {{
    background: #f8fafc;
    color: #475569;
    font-weight: 600;
    padding: 12px 18px;
    border-bottom: 1px solid var(--border);
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}}
td {{
    padding: 14px 18px;
    border-bottom: 1px solid #f1f5f9;
    vertical-align: middle;
}}
tr:hover td {{ background: #f8fafc; }}

.badge {{
    font-size: 11px;
    font-weight: 700;
    padding: 3px 8px;
    border-radius: 6px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    display: inline-block;
}}
.badge-drop {{
    background: #fee2e2;
    color: #b91c1c;
    border: 1px solid #fca5a5;
}}
.speedup-tag {{
    font-weight: 700;
    color: #059669;
    background: #ecfdf5;
    padding: 3px 8px;
    border-radius: 6px;
    border: 1px solid #a7f3d0;
    font-size: 12px;
}}

/* SQL Code Cell & Copy */
.sql-cell {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    background: #f1f5f9;
    padding: 6px 12px;
    border-radius: 6px;
    border: 1px solid #e2e8f0;
}}
.sql-cell code {{
    font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace;
    font-size: 12px;
    color: #0f172a;
    word-break: break-all;
}}
.sql-drop {{ color: #b91c1c !important; }}
.btn-copy-sm {{
    background: #ffffff;
    border: 1px solid #cbd5e1;
    color: #334155;
    font-size: 11px;
    padding: 4px 8px;
    border-radius: 4px;
    font-weight: 600;
    cursor: pointer;
    white-space: nowrap;
}}
.btn-copy-sm:hover {{ background: #f8fafc; border-color: #94a3b8; }}

/* Workbench Code Area */
.workbench-box {{
    background: #0f172a;
    color: #f8fafc;
    border-radius: 12px;
    padding: 24px;
    position: relative;
    box-shadow: 0 4px 15px rgba(0,0,0,0.1);
}}
.workbench-header {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 16px;
}}
.workbench-title {{
    font-size: 14px;
    font-weight: 600;
    color: #94a3b8;
    text-transform: uppercase;
}}
.btn-copy-main {{
    background: var(--primary);
    color: #ffffff;
    border: none;
    padding: 8px 16px;
    border-radius: 6px;
    font-size: 13px;
    font-weight: 600;
    cursor: pointer;
    transition: background 0.2s;
}}
.btn-copy-main:hover {{ background: var(--primary-dark); }}
.workbench-textarea {{
    width: 100%;
    height: 320px;
    background: #1e293b;
    border: 1px solid #334155;
    border-radius: 8px;
    color: #f1f5f9;
    font-family: "SFMono-Regular", Consolas, monospace;
    font-size: 13px;
    padding: 16px;
    resize: vertical;
}}

/* Toast Notification */
#toast {{
    visibility: hidden;
    min-width: 200px;
    background-color: #0f172a;
    color: #fff;
    text-align: center;
    border-radius: 8px;
    padding: 12px 20px;
    position: fixed;
    z-index: 1000;
    left: 50%;
    bottom: 30px;
    transform: translateX(-50%);
    font-size: 14px;
    font-weight: 600;
    border: 1px solid #334155;
}}
#toast.show {{
    visibility: visible;
    animation: fadein 0.3s, fadeout 0.3s 2s;
}}
@keyframes fadein {{ from {{ bottom: 10px; opacity: 0; }} to {{ bottom: 30px; opacity: 1; }} }}
@keyframes fadeout {{ from {{ bottom: 30px; opacity: 1; }} to {{ bottom: 10px; opacity: 0; }} }}
</style>
</head>
<body>

<header>
    <div class="header-top">
        <div class="header-brand">
            <h1>🛡️ DbIndex Analyzer</h1>
            <span class="header-badge">Production Audit Engine</span>
        </div>
        <div>
            <button class="btn-copy-main" onclick="window.print()">🖨️ Print / Save PDF</button>
        </div>
    </div>
    <div class="header-meta">
        Database: <b>{esc(db_name)}</b> &nbsp;|&nbsp;
        Engine: <b>{esc(engine_type.upper())}</b> &nbsp;|&nbsp;
        Analyzed: <b>{datetime.now():%Y-%m-%d %H:%M:%S}</b> &nbsp;|&nbsp;
        Status: <b style="color:#10b981;">Ready for Production Review</b>
    </div>
</header>

<div class="container">
    <!-- Key Health Metrics Grid -->
    <div class="metrics-grid">
        <div class="card score-card">
            <div class="score-circle">
                <span class="score-val">{score}</span>
                <span class="score-grade">Grade {grade}</span>
            </div>
            <div>
                <div class="stat-title">Schema Health Score</div>
                <div style="font-size:13px; color:#475569; margin-top:4px;">
                    {f"Optimal performance" if score >= 85 else f"Needs tuning" if score >= 60 else "Critical bottlenecks"}
                </div>
            </div>
        </div>

        <div class="card">
            <div class="stat-title">Database Inventory</div>
            <div class="stat-num">{table_count}</div>
            <div class="stat-sub">{column_count} columns scanned</div>
        </div>

        <div class="card">
            <div class="stat-title">Existing Indexes</div>
            <div class="stat-num">{total_existing}</div>
            <div class="stat-sub">Active in catalog</div>
        </div>

        <div class="card">
            <div class="stat-title">Missing Indexes</div>
            <div class="stat-num" style="color:var(--danger);">{len(suggestions)}</div>
            <div class="stat-sub">Action: CREATE</div>
        </div>

        <div class="card">
            <div class="stat-title">Redundant Indexes</div>
            <div class="stat-num" style="color:var(--warning);">{len(redundant)}</div>
            <div class="stat-sub">Action: DROP</div>
        </div>

        <div class="card">
            <div class="stat-title">Key Coverage</div>
            <div class="stat-num">{pk_cov}%</div>
            <div class="stat-sub">FK Indexing: {fk_cov}%</div>
        </div>
    </div>

    <!-- Architectural Insights Box -->
    <div class="insights-box">
        <h3>🔍 Architectural & Schema Observations</h3>
        <ul>
            {insights_html}
        </ul>
    </div>

    <!-- Tabs Navigation -->
    <div class="tabs-header">
        <button class="tab-btn active" onclick="switchTab('tab-missing')">
            🚀 Missing Indexes <span class="pill-count">{len(suggestions)}</span>
        </button>
        <button class="tab-btn" onclick="switchTab('tab-redundant')">
            🧹 Redundant & Wasteful Indexes <span class="pill-count">{len(redundant)}</span>
        </button>
        <button class="tab-btn" onclick="switchTab('tab-healthy')">
            🛡️ Existing Healthy Indexes <span class="pill-count">{len(healthy)}</span>
        </button>
        <button class="tab-btn" onclick="switchTab('tab-schema')">
            📚 Database Schema Knowledge <span class="pill-count">{table_count} tables</span>
        </button>
        <button class="tab-btn" onclick="switchTab('tab-workbench')">
            ⚡ SQL Migration Scripts
        </button>
    </div>

    <!-- TAB 1: MISSING INDEXES -->
    <div id="tab-missing" class="tab-content">
        <div class="filter-bar">
            <input type="text" id="search-missing" class="search-input" placeholder="Filter by table, column, or reason..." onkeyup="filterTable('missing-table', this.value)">
            <span style="font-size:13px; color:#64748b;">Columns where creating an index delivers substantial query speedups</span>
        </div>
        <div class="table-container">
            <table id="missing-table">
                <thead>
                    <tr>
                        <th>Target Column</th>
                        <th>Severity</th>
                        <th>Architectural Reason</th>
                        <th>Speedup Estimate</th>
                        <th>Executable SQL (CREATE)</th>
                    </tr>
                </thead>
                <tbody>
                    {"".join(missing_rows) if missing_rows else '<tr><td colspan="5" style="text-align:center; padding:30px; color:#64748b;">No missing indexes detected. Your database schema is well-indexed!</td></tr>'}
                </tbody>
            </table>
        </div>
    </div>

    <!-- TAB 2: REDUNDANT INDEXES -->
    <div id="tab-redundant" class="tab-content" style="display:none;">
        <div class="filter-bar">
            <input type="text" id="search-redundant" class="search-input" placeholder="Filter redundant indexes..." onkeyup="filterTable('redundant-table', this.value)">
            <span style="font-size:13px; color:#64748b;">Indexes that duplicate existing structures or cover redundant prefixes</span>
        </div>
        <div class="table-container">
            <table id="redundant-table">
                <thead>
                    <tr>
                        <th>Table</th>
                        <th>Existing Index Name</th>
                        <th>Issue Type</th>
                        <th>Why It Is Wasteful</th>
                        <th>Safe Cleanup Command (DROP)</th>
                    </tr>
                </thead>
                <tbody>
                    {"".join(redundant_rows) if redundant_rows else '<tr><td colspan="5" style="text-align:center; padding:30px; color:#64748b;">Zero duplicate or redundant indexes detected. No wasted write I/O found.</td></tr>'}
                </tbody>
            </table>
        </div>
    </div>

    <!-- TAB 3: HEALTHY INDEXES -->
    <div id="tab-healthy" class="tab-content" style="display:none;">
        <div class="filter-bar">
            <input type="text" id="search-healthy" class="search-input" placeholder="Filter healthy indexes..." onkeyup="filterTable('healthy-table', this.value)">
            <span style="font-size:13px; color:#64748b;">Catalog of verified healthy Primary Keys, Unique Constraints, and Secondary Indexes</span>
        </div>
        <div class="table-container">
            <table id="healthy-table">
                <thead>
                    <tr>
                        <th>Table</th>
                        <th>Index Name</th>
                        <th>Indexed Columns</th>
                        <th>Index Classification</th>
                        <th>Operational Function</th>
                    </tr>
                </thead>
                <tbody>
                    {"".join(healthy_rows) if healthy_rows else '<tr><td colspan="5" style="text-align:center; padding:30px; color:#64748b;">No existing indexes found in catalog.</td></tr>'}
                </tbody>
            </table>
        </div>
    </div>

    <!-- TAB 4: SCHEMA KNOWLEDGE -->
    <div id="tab-schema" class="tab-content" style="display:none;">
        <div class="filter-bar">
            <input type="text" id="search-schema" class="search-input" placeholder="Filter tables..." onkeyup="filterTable('schema-table', this.value)">
            <span style="font-size:13px; color:#64748b;">Comprehensive relational catalog of tables, keys, and constraint coverage</span>
        </div>
        <div class="table-container">
            <table id="schema-table">
                <thead>
                    <tr>
                        <th>Table Name</th>
                        <th>Column Count</th>
                        <th>Primary Key</th>
                        <th>Foreign Keys</th>
                        <th>Total Indexes</th>
                        <th>Column Signatures</th>
                    </tr>
                </thead>
                <tbody>
                    {"".join(schema_rows) if schema_rows else '<tr><td colspan="6" style="text-align:center; padding:30px; color:#64748b;">Schema details unavailable.</td></tr>'}
                </tbody>
            </table>
        </div>
    </div>

    <!-- TAB 5: SQL WORKBENCH -->
    <div id="tab-workbench" class="tab-content" style="display:none;">
        <div class="workbench-box">
            <div class="workbench-header">
                <span class="workbench-title">Complete Executable Migration Plan</span>
                <div>
                    <button class="btn-copy-main" onclick="copyFromTextarea('workbench-sql')">📋 Copy Full Migration Script</button>
                </div>
            </div>
            <textarea id="workbench-sql" class="workbench-textarea" readonly>{esc(combined_sql)}</textarea>
        </div>
    </div>
</div>

<div id="toast">Copied to clipboard!</div>

<script>
function switchTab(tabId) {{
    document.querySelectorAll('.tab-content').forEach(el => el.style.display = 'none');
    document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
    document.getElementById(tabId).style.display = 'block';
    event.currentTarget.classList.add('active');
}}

function filterTable(tableId, query) {{
    const q = query.toLowerCase().trim();
    const rows = document.querySelectorAll('#' + tableId + ' tbody tr');
    rows.forEach(r => {{
        const text = r.innerText.toLowerCase();
        r.style.display = text.includes(q) ? '' : 'none';
    }});
}}

function showToast(msg) {{
    const t = document.getElementById('toast');
    t.innerText = msg;
    t.className = 'show';
    setTimeout(() => {{ t.className = t.className.replace('show', ''); }}, 2200);
}}

function copySnippet(text) {{
    navigator.clipboard.writeText(text).then(() => {{
        showToast('SQL snippet copied!');
    }});
}}

function copyFromTextarea(id) {{
    const ta = document.getElementById(id);
    navigator.clipboard.writeText(ta.value).then(() => {{
        showToast('Full migration script copied!');
    }});
}}
</script>

</body>
</html>
"""

    with open(path, "w", encoding="utf-8") as f:
        f.write(html_content)
