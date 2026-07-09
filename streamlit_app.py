import hashlib
import re
import sqlite3
import tempfile
from pathlib import Path

import streamlit as st

DB_PATH = Path(tempfile.gettempdir()) / "arthi_demo.db"

# ---------------------------------------------------------------------------
# Data layer
# ---------------------------------------------------------------------------


@st.cache_resource
def get_connection():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS demo_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL,
            company TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS demo_projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            client_name TEXT NOT NULL,
            client_email TEXT NOT NULL,
            tier TEXT NOT NULL,
            location TEXT NOT NULL,
            status TEXT NOT NULL,
            progress_percent INTEGER NOT NULL,
            budget REAL NOT NULL,
            spent REAL NOT NULL,
            expected_handover TEXT NOT NULL,
            engineer_name TEXT NOT NULL,
            ai_insight TEXT NOT NULL,
            description TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS demo_updates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            message TEXT NOT NULL,
            phase TEXT NOT NULL,
            image_label TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY(project_id) REFERENCES demo_projects(id) ON DELETE CASCADE
        )
        """
    )
    conn.commit()

    user_count = conn.execute("SELECT COUNT(*) AS count FROM demo_users").fetchone()["count"]
    if user_count == 0:
        users = [
            ("Aarav Sharma", "admin@arthi.com", "arthi123", "Admin", "Arthi Construction"),
            ("Nisha Patel", "engineer@arthi.com", "engineer123", "Engineer", "Arthi Construction"),
            ("Rohan Menon", "customer@arthi.com", "customer123", "Customer", "Arthi Construction"),
        ]
        conn.executemany(
            "INSERT INTO demo_users (name, email, password, role, company) VALUES (?, ?, ?, ?, ?)",
            [(name, email, hashlib.sha256(password.encode()).hexdigest(), role, company) for name, email, password, role, company in users],
        )

    project_count = conn.execute("SELECT COUNT(*) AS count FROM demo_projects").fetchone()["count"]
    if project_count == 0:
        projects = [
            (
                "Villa Alpha - Full Build",
                "Rohan Menon",
                "customer@arthi.com",
                "Full Build",
                "Bangalore",
                "In Progress",
                72,
                4200000,
                3020000,
                "Aug 20, 2026",
                "Nisha Patel",
                "Foundation and structural work are on schedule. Roofing and electrical rough-in are next.",
                "Luxury villa with premium interiors and smart home automation.",
            ),
            (
                "Shell House - North Plot",
                "Meera Iyer",
                "meera@arthi.com",
                "Shell / Half Done",
                "Hyderabad",
                "Awaiting Interiors",
                64,
                2100000,
                1380000,
                "Sep 10, 2026",
                "Amit Rao",
                "Structure is complete. The client can now plan their interior fit-out and approvals.",
                "Shell house for a customer who will handle finishing and interiors later.",
            ),
            (
                "Apartment Block - Tower B",
                "Prakash Group",
                "prakash@arthi.com",
                "Apartment / Multi Unit",
                "Chennai",
                "Milestone Review",
                88,
                9800000,
                8640000,
                "Oct 01, 2026",
                "Karthik S",
                "Apartment block is ahead of schedule on plumbing and common areas. Vendor delivery is stable.",
                "Multi-unit residential project with shared amenities and phase-wise delivery.",
            ),
        ]
        conn.executemany(
            "INSERT INTO demo_projects (name, client_name, client_email, tier, location, status, progress_percent, budget, spent, expected_handover, engineer_name, ai_insight, description) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            projects,
        )
        conn.commit()
        project_ids = [row[0] for row in conn.execute("SELECT id FROM demo_projects ORDER BY id").fetchall()]
        updates = [
            (project_ids[0], "Foundation Completed", "Concrete base and steel reinforcement were completed successfully.", "Foundation", "foundation", "2026-07-08"),
            (project_ids[0], "Wall Structure Progress", "Brickwork and framing are progressing as planned for the next phase.", "Structure", "structure", "2026-07-08"),
            (project_ids[1], "Shell Ready for Interiors", "The structural shell is complete and the client can begin interior planning.", "Shell Completion", "shell", "2026-07-08"),
            (project_ids[2], "Common Area Milestone", "Plumbing and flooring have reached the final review checkpoint.", "Finishing", "apartment", "2026-07-08"),
        ]
        conn.executemany(
            "INSERT INTO demo_updates (project_id, title, message, phase, image_label, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            updates,
        )

    conn.commit()


def authenticate(email: str, password: str):
    conn = get_connection()
    hashed = hashlib.sha256(password.encode()).hexdigest()
    row = conn.execute(
        "SELECT id, name, email, role, company FROM demo_users WHERE email = ? AND password = ?",
        (email, hashed),
    ).fetchone()
    return dict(row) if row else None


def get_projects():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM demo_projects ORDER BY id").fetchall()
    return [dict(row) for row in rows]


def get_updates(project_id: int):
    conn = get_connection()
    rows = conn.execute("SELECT * FROM demo_updates WHERE project_id = ? ORDER BY id DESC", (project_id,)).fetchall()
    return [dict(row) for row in rows]


# ---------------------------------------------------------------------------
# Rule-based "AI" layer — deliberately simple and auditable for the prototype
# stage, exactly as described in the pitch: rule-based first, ML later once
# there is real project history to train on.
# ---------------------------------------------------------------------------

PHASE_MAP = {
    "Full Build": ["Foundation", "Structure", "Roofing & MEP", "Interiors", "Handover"],
    "Shell / Half Done": ["Foundation", "Structure", "Shell Complete"],
    "Apartment / Multi Unit": ["Foundation", "Structure", "Common Areas & MEP", "Finishing", "Handover"],
}


def get_phase_state(project):
    phases = PHASE_MAP.get(project["tier"], ["Foundation", "Structure", "Finishing", "Handover"])
    pct = project["progress_percent"] / 100
    band = 1 / len(phases)
    current_index = min(int(pct / band), len(phases) - 1)
    fraction = min(max((pct - current_index * band) / band, 0), 1) if pct < 1 else 1.0
    return phases, current_index, fraction


def get_risk(project):
    """A transparent, rule-based delay signal: compares spend pace to build
    pace. This is intentionally simple — the pitch is explicit that the
    predictive model should start as rules and graduate to a trained model
    once there's enough project history."""
    budget_ratio = project["spent"] / project["budget"] if project["budget"] else 0
    progress_ratio = project["progress_percent"] / 100
    gap = budget_ratio - progress_ratio
    if gap > 0.10:
        return {
            "level": "risk",
            "label": "Needs review",
            "message": "Spend is running ahead of physical progress. Worth a quick check-in with the site engineer.",
        }
    if gap > 0.04:
        return {
            "level": "watch",
            "label": "Keep watching",
            "message": "Spend and progress are close, but drifting slightly. No action needed yet.",
        }
    return {
        "level": "on_track",
        "label": "On track",
        "message": "Spend pace matches build progress.",
    }


def answer_question(query, project, updates):
    q = query.lower()

    def money(v):
        return f"₹{v:,.0f}"

    if re.search(r"budget|cost|spend|spent|money", q):
        remaining = project["budget"] - project["spent"]
        return (
            f"{money(project['spent'])} has been spent of a {money(project['budget'])} budget "
            f"— {money(remaining)} remaining."
        )
    if re.search(r"progress|percent|how far|done|complete", q):
        phases, idx, frac = get_phase_state(project)
        return (
            f"{project['name']} is {project['progress_percent']}% complete, currently in the "
            f"'{phases[idx]}' phase. Status: {project['status']}."
        )
    if re.search(r"when|eta|handover|finish|deadline|delivery", q):
        return f"Expected handover is {project['expected_handover']}."
    if re.search(r"engineer|who.*(site|assigned|charge)", q):
        return f"{project['engineer_name']} is the site engineer assigned to this project."
    if re.search(r"delay|risk|behind|on.?track", q):
        risk = get_risk(project)
        return f"{risk['label']}: {risk['message']}"
    if re.search(r"plumbing|electrical|roof|wall|foundation|structure|interior", q):
        return project["ai_insight"]
    if updates:
        latest = updates[0]
        if re.search(r"latest|update|news|recent", q):
            return f"Latest update — {latest['title']}: {latest['message']}"
    return (
        "I can answer questions about progress, budget, timeline, delay risk, or the assigned "
        "engineer for this project. Try asking something like \"is the plumbing done?\" or "
        "\"when is handover?\""
    )


# ---------------------------------------------------------------------------
# Design system — "site blueprint": navy/paper/amber, evoking a construction
# drawing set rather than a generic SaaS dashboard.
# ---------------------------------------------------------------------------

def inject_theme():
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&family=Inter:wght@400;500;600&family=IBM+Plex+Mono:wght@500;600&display=swap');

        :root {
            --navy: #16233F;
            --navy-2: #1F3358;
            --paper: #EFEAE0;
            --paper-line: #D9D0BC;
            --amber: #E2932E;
            --amber-dark: #B9721A;
            --slate: #5C6B7C;
            --green: #3F7D58;
            --red: #B5482F;
            --white: #FFFFFF;
            --ink: #1B2432;
        }

        html, body, [class*="css"] { font-family: 'Inter', sans-serif; color: var(--ink); }
        h1, h2, h3, h4, h5, h6, .display-font {
        font-family: 'Space Grotesk', sans-serif;
        color: var(--navy) !important;
        }
        
        .hero-panel h1,
        .hero-panel .hero-title,
        .hero-panel .hero-subtitle {
        color: #F2F0E9 !important;
        }
        
        [data-testid="stExpander"] summary,
        [data-testid="stExpander"] summary p,
        .streamlit-expanderHeader {
        color: var(--ink) !important;
        font-weight: 600 !important;
        }
        
        [data-testid="stCaptionContainer"],
        [data-testid="stCaptionContainer"] p {
        color: var(--slate) !important;
        }
        
        .risk-ontrack, .risk-ontrack * { color: #235436 !important; }
        .risk-watch, .risk-watch * { color: #7A4E10 !important; }
        .risk-risk, .risk-risk * { color: #7C2C18 !important; }

        .stApp {
            background:
                repeating-linear-gradient(0deg, var(--paper-line) 0px, var(--paper-line) 1px, transparent 1px, transparent 88px),
                repeating-linear-gradient(90deg, var(--paper-line) 0px, var(--paper-line) 1px, transparent 1px, transparent 88px),
                var(--paper);
            background-attachment: fixed;
        }
        [data-testid="stSidebar"] { background: var(--navy); }
        [data-testid="stSidebar"] * { color: #E7E9EE !important; }

        /* Blueprint corner-mark card */
        .bp-card {
            position: relative;
            background: var(--white);
            border: 1px solid #D8D2C4;
            border-radius: 4px;
            padding: 1.6rem 1.8rem;
            margin-bottom: 1.4rem;
        }
        .bp-card::before, .bp-card::after {
            content: "";
            position: absolute;
            width: 14px; height: 14px;
            border-color: var(--amber);
            border-style: solid;
        }
        .bp-card::before { top: -1px; left: -1px; border-width: 3px 0 0 3px; }
        .bp-card::after { bottom: -1px; right: -1px; border-width: 0 3px 3px 0; }

        .eyebrow {
            font-family: 'IBM Plex Mono', monospace;
            font-size: 0.72rem;
            letter-spacing: 0.14em;
            text-transform: uppercase;
            color: var(--amber-dark);
            margin-bottom: 0.35rem;
        }

        .hero-panel {
            background: linear-gradient(155deg, var(--navy) 0%, var(--navy-2) 100%);
            border-radius: 6px;
            padding: 2.6rem 2.4rem;
            color: #F2F0E9;
            position: relative;
            overflow: hidden;
        }
        .hero-panel::after {
            content: "";
            position: absolute; inset: 0;
            background: repeating-linear-gradient(45deg, rgba(226,147,46,0.06) 0 2px, transparent 2px 26px);
        }
        .hero-title { font-size: 2.6rem; font-weight: 700; margin: 0 0 0.5rem 0; position: relative; }
        .hero-subtitle { color: #B9C2D0; font-size: 1.02rem; max-width: 640px; position: relative; }

        .metric-card {
            background: var(--white);
            border: 1px solid #D8D2C4;
            border-left: 3px solid var(--amber);
            border-radius: 4px;
            padding: 1.1rem 1.3rem;
        }
        .metric-label {
            font-family: 'IBM Plex Mono', monospace;
            font-size: 0.7rem; letter-spacing: 0.1em; text-transform: uppercase;
            color: var(--slate); margin-bottom: 0.4rem;
        }
        .metric-value { font-size: 2rem; font-weight: 600; color: var(--navy); }

        .badge {
            display: inline-block;
            font-family: 'IBM Plex Mono', monospace;
            font-size: 0.72rem; font-weight: 600; letter-spacing: 0.03em;
            padding: 0.3rem 0.7rem; border-radius: 999px; margin-right: 0.4rem;
        }
        .badge-navy { background: #E4E8F0; color: var(--navy); }
        .badge-ontrack { background: #E1EFE5; color: var(--green); }
        .badge-watch { background: #FBEBD3; color: var(--amber-dark); }
        .badge-risk { background: #F6DFD8; color: var(--red); }

        .risk-banner {
            border-radius: 4px; padding: 0.9rem 1.2rem; margin: 0.9rem 0;
            font-size: 0.92rem; border-left: 4px solid;
        }
        .risk-ontrack { background: #EDF6EF; border-color: var(--green); color: #235436; }
        .risk-watch { background: #FDF3E3; border-color: var(--amber); color: #7A4E10; }
        .risk-risk { background: #FBEAE5; border-color: var(--red); color: #7C2C18; }

        /* Timeline / ruler */
        .timeline-wrap { margin: 1.1rem 0 0.4rem 0; }
        .timeline-track { position: relative; height: 6px; background: #E4DFD1; border-radius: 3px; margin: 0 10px; }
        .timeline-fill { position: absolute; top: 0; left: 0; height: 6px; background: var(--amber); border-radius: 3px; }
        .timeline-nodes { display: flex; justify-content: space-between; margin-top: -3px; padding: 0 2px; }
        .timeline-node { width: 12px; height: 12px; border-radius: 50%; background: #E4DFD1; border: 2px solid var(--white); margin-top: -3px; }
        .timeline-node.done { background: var(--amber); }
        .timeline-node.current { background: var(--navy); box-shadow: 0 0 0 4px rgba(22,35,63,0.15); }
        .timeline-labels { display: flex; justify-content: space-between; margin-top: 0.5rem; }
        .timeline-labels span {
            font-family: 'IBM Plex Mono', monospace; font-size: 0.68rem; color: var(--slate);
            text-align: center; flex: 1;
        }
        .timeline-labels span.active { color: var(--navy); font-weight: 700; }

        .photo-chip {
            display: inline-flex; align-items: center; gap: 0.4rem;
            background: #F0EDE4; border: 1px dashed #C9C1AE; border-radius: 4px;
            padding: 0.35rem 0.7rem; font-size: 0.78rem; color: var(--slate);
            font-family: 'IBM Plex Mono', monospace;
        }

        .stTabs [data-baseweb="tab"] { font-family: 'Space Grotesk', sans-serif; font-weight: 600; }
        .stButton>button {
            background: var(--amber); color: white; border: none; border-radius: 4px;
            font-weight: 600; font-family: 'Inter', sans-serif;
        }
        .stButton>button:hover { background: var(--amber-dark); color: white; }
        </style>
        """,
        unsafe_allow_html=True,
    )


PHASE_ICON = {
    "foundation": "▦", "structure": "▤", "shell": "▥", "apartment": "▧",
}


def render_timeline(project):
    phases, current_index, frac = get_phase_state(project)
    n = len(phases)
    fill_pct = ((current_index + frac) / n) * 100
    nodes_html = ""
    labels_html = ""
    for i, phase in enumerate(phases):
        cls = "done" if i < current_index else ("current" if i == current_index else "")
        nodes_html += f'<div class="timeline-node {cls}"></div>'
        label_cls = "active" if i == current_index else ""
        labels_html += f'<span class="{label_cls}">{phase}</span>'
    html = f"""
    <div class="timeline-wrap">
        <div class="timeline-track">
            <div class="timeline-fill" style="width:{fill_pct:.1f}%"></div>
        </div>
        <div class="timeline-nodes">{nodes_html}</div>
        <div class="timeline-labels">{labels_html}</div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


def render_risk_banner(project):
    risk = get_risk(project)
    st.markdown(
        f'<div class="risk-banner risk-{risk["level"]}"><strong>{risk["label"]}.</strong> {risk["message"]}</div>',
        unsafe_allow_html=True,
    )
    return risk


def render_ask_ai(projects, key_prefix, default_project_id=None):
    st.markdown('<div class="eyebrow">Ask about a project</div>', unsafe_allow_html=True)
    if len(projects) > 1:
        options = {p["name"]: p["id"] for p in projects}
        chosen_name = st.selectbox("Project", list(options.keys()), key=f"{key_prefix}_proj_select")
        project_id = options[chosen_name]
    else:
        project_id = projects[0]["id"]
    project = next(p for p in projects if p["id"] == project_id)
    updates = get_updates(project_id)

    st.caption("This runs on simple, transparent rules today — the same approach the platform "
               "uses everywhere until there's enough project history to train a model on.")
    query = st.text_input("Type a question, e.g. \"is the plumbing done?\"", key=f"{key_prefix}_q")
    if query:
        st.markdown(
            f'<div class="bp-card"><div class="eyebrow">Answer</div>{answer_question(query, project, updates)}</div>',
            unsafe_allow_html=True,
        )
    with st.expander("Suggested questions"):
        for sample in ["What's the current progress?", "How much budget is left?", "When is handover?", "Are we at risk of delay?"]:
            st.markdown(f"- {sample}")


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

init_db()

st.set_page_config(page_title="Arthi Construction Demo", page_icon="🏗️", layout="wide")
inject_theme()

if "user" not in st.session_state:
    st.session_state.user = None
if "signoffs" not in st.session_state:
    st.session_state.signoffs = set()

if st.session_state.user is None:
    st.markdown(
        """
        <div class='hero-panel'>
            <div class="eyebrow" style="color:#E2932E;">ARTHI CONSTRUCTION · CLIENT PLATFORM</div>
            <h1 class='hero-title'>Watch your build happen, in real time.</h1>
            <p class='hero-subtitle'>One shared record for admins, engineers, and customers — live progress,
            verified updates, and a straight answer to "what stage are we at," any time you ask.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.sidebar.header("Demo Credentials")
    st.sidebar.info("Sign in with any of these demo accounts")
    st.sidebar.code("admin@arthi.com / arthi123\nengineer@arthi.com / engineer123\ncustomer@arthi.com / customer123")

    left, right = st.columns([1, 1.3], gap="large")
    with left:
        st.markdown('<div class="bp-card">', unsafe_allow_html=True)
        with st.form("login"):
            st.markdown('<div class="eyebrow">Sign in</div>', unsafe_allow_html=True)
            email = st.text_input("Email", value="admin@arthi.com")
            password = st.text_input("Password", value="arthi123", type="password")
            submitted = st.form_submit_button("Access demo")
            if submitted:
                user = authenticate(email, password)
                if user:
                    st.session_state.user = user
                    st.rerun()
                else:
                    st.error("Invalid credentials")
        st.markdown('</div>', unsafe_allow_html=True)

    with right:
        st.markdown(
            """
            <div class='bp-card'>
                <div class="eyebrow">What this demo highlights</div>
                <ul style="color:#334155; margin-top:0.6rem;">
                    <li>A visual site timeline instead of a status paragraph</li>
                    <li>Ask-a-question chat grounded in real project data, no guessing</li>
                    <li>A plain-language delay signal, not a black-box score</li>
                    <li>The same live data behind admin, engineer, and customer views</li>
                </ul>
            </div>
            """,
            unsafe_allow_html=True,
        )
else:
    user = st.session_state.user
    st.sidebar.markdown(f"### {user['name']}")
    st.sidebar.write(f"Role: {user['role']}")
    st.sidebar.write(f"Company: {user['company']}")
    if st.sidebar.button("Logout"):
        st.session_state.user = None
        st.rerun()

    all_projects = get_projects()
    if user["role"] == "Customer":
        projects = [p for p in all_projects if p["client_email"] == user["email"]]
    elif user["role"] == "Engineer":
        projects = [p for p in all_projects if p["engineer_name"] == user["name"]]
    else:
        projects = all_projects

    if not projects:
        st.warning("No projects found for your account.")
        st.stop()

    total_projects = len(projects)
    avg_progress = round(sum(p["progress_percent"] for p in projects) / total_projects, 1) if total_projects else 0
    active_projects = sum(1 for p in projects if p["status"] != "Completed")
    completed_projects = sum(1 for p in projects if p["status"] == "Completed")
    at_risk = sum(1 for p in projects if get_risk(p)["level"] == "risk")

    if user["role"] == "Admin":
        header_text = "Arthi Construction Control Center"
        subtitle = "Full executive view across every project, tier, and customer."
        cards = [("Total Projects", total_projects), ("Active", active_projects), ("Needs Review", at_risk), ("Avg Progress", f"{avg_progress}%")]
        tabs = ["Dashboard", "Updates", "Customer View", "Ask AI"]
    elif user["role"] == "Engineer":
        header_text = "Engineer Dashboard"
        subtitle = "Your assigned sites and field updates."
        cards = [("Assigned", total_projects), ("Active Sites", active_projects), ("Avg Progress", f"{avg_progress}%")]
        tabs = ["My Projects", "Updates", "Ask AI"]
    else:
        header_text = "Customer Project Portal"
        subtitle = "Your project, your timeline, your questions answered."
        cards = [("My Projects", total_projects), ("Avg Progress", f"{avg_progress}%")]
        tabs = ["Project Summary", "Updates", "Ask AI"]

    st.markdown(f"<h1 class='display-font' style='font-size:2.5rem;margin-bottom:0.1rem;'>{header_text}</h1><p style='color:#5C6B7C;'>{subtitle}</p>", unsafe_allow_html=True)

    columns = st.columns(len(cards), gap="medium")
    for col, (title, value) in zip(columns, cards):
        col.markdown(f"<div class='metric-card'><div class='metric-label'>{title}</div><div class='metric-value'>{value}</div></div>", unsafe_allow_html=True)

    st.write("")
    tab_objs = st.tabs(tabs)
    tab_map = dict(zip(tabs, tab_objs))

    primary_key = tabs[0]
    with tab_map[primary_key]:
        for project in projects:
            st.markdown('<div class="bp-card">', unsafe_allow_html=True)
            badge_html = f'<span class="badge badge-navy">{project["tier"]}</span><span class="badge badge-navy">{project["location"]}</span>'
            st.markdown(
                f"<div class='eyebrow'>{project['status']}</div><h3 style='margin:0 0 0.3rem 0;'>{project['name']}</h3>{badge_html}",
                unsafe_allow_html=True,
            )
            st.write(project["description"])
            render_timeline(project)
            risk = render_risk_banner(project)

            c1, c2, c3 = st.columns(3)
            c1.markdown(f"<div class='metric-label'>Budget used</div><div class='money' style='font-size:1.2rem;'>₹{project['spent']:,.0f} / ₹{project['budget']:,.0f}</div>", unsafe_allow_html=True)
            c2.markdown(f"<div class='metric-label'>Expected handover</div><div style='font-size:1.1rem;'>{project['expected_handover']}</div>", unsafe_allow_html=True)
            c3.markdown(f"<div class='metric-label'>Engineer</div><div style='font-size:1.1rem;'>{project['engineer_name']}</div>", unsafe_allow_html=True)

            st.info(f"AI insight: {project['ai_insight']}")

            if project["tier"] == "Shell / Half Done" and "Awaiting" in project["status"] and user["role"] == "Customer":
                signoff_key = f"signoff_{project['id']}"
                if signoff_key in st.session_state.signoffs:
                    st.success("You approved this milestone — interior planning can begin.")
                else:
                    if st.button("Approve shell-to-interior milestone", key=f"btn_{signoff_key}"):
                        st.session_state.signoffs.add(signoff_key)
                        st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

    with tab_map["Updates"]:
        for project in projects:
            st.markdown(f"<h4 style='margin-bottom:0.3rem;'>{project['name']}</h4>", unsafe_allow_html=True)
            updates = get_updates(project["id"])
            for update in updates:
                with st.expander(f"{update['title']} — {update['phase']}"):
                    icon = PHASE_ICON.get(update["image_label"], "▦")
                    st.markdown(f'<span class="photo-chip">{icon} site photo · {update["phase"]}</span>', unsafe_allow_html=True)
                    st.write(update["message"])
                    st.caption(f"Updated on {update['created_at']}")
            st.divider()

    with tab_map["Ask AI"]:
        render_ask_ai(projects, key_prefix=user["role"].lower())

    if user["role"] == "Admin":
        with tab_map["Customer View"]:
            st.caption("This is exactly what the customer sees for each project — no separate admin-only data leaks through.")
            for project in projects:
                st.markdown('<div class="bp-card">', unsafe_allow_html=True)
                st.markdown(f"<h4 style='margin:0 0 0.3rem 0;'>{project['name']}</h4><div class='eyebrow'>{project['client_name']}</div>", unsafe_allow_html=True)
                render_timeline(project)
                render_risk_banner(project)
                st.markdown(f"<div class='money'>₹{project['spent']:,.0f} / ₹{project['budget']:,.0f} spent · handover {project['expected_handover']}</div>", unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)
