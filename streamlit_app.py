import hashlib
import sqlite3
from pathlib import Path

import streamlit as st

DB_PATH = Path(__file__).resolve().parent / "demo.db"


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
                "customer@arthi.com",
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
                "customer@arthi.com",
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


init_db()

st.set_page_config(page_title="Arthi Construction Demo", page_icon="🏗️", layout="wide")

if "user" not in st.session_state:
    st.session_state.user = None

if st.session_state.user is None:
    st.markdown(
        """
        <style>
        .hero-card {background: linear-gradient(135deg, #0f172a, #111827); border-radius: 1.5rem; padding: 2rem; color: white;}
        .hero-title {font-size: 3rem; margin-bottom: 0.4rem;}
        .hero-subtitle {color: #cbd5e1; font-size: 1.05rem; margin-top: 0;}
        .feature-box {background: #ffffff; border-radius: 1rem; padding: 1.5rem; margin-top: 1.5rem; box-shadow: 0 16px 40px rgba(15, 23, 42, 0.08);}
        .feature-box ul {margin: 0.75rem 0 0 1rem; color: #334155;}
        .feature-box li {margin-bottom: 0.6rem;}
        </style>
        <div class='hero-card'>
            <h1 class='hero-title'>Arthi Construction AI Demo</h1>
            <p class='hero-subtitle'>A polished presentation dashboard for client communication and construction progress tracking.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.sidebar.header("Demo Credentials")
    st.sidebar.info("Sign in with any of these demo accounts")
    st.sidebar.code("admin@arthi.com / arthi123\nengineer@arthi.com / engineer123\ncustomer@arthi.com / customer123")

    with st.form("login"):
        email = st.text_input("Email", value="admin@arthi.com")
        password = st.text_input("Password", value="arthi123", type="password")
        submitted = st.form_submit_button("Access Demo")
        if submitted:
            user = authenticate(email, password)
            if user:
                st.session_state.user = user
                st.experimental_rerun()
            else:
                st.error("Invalid credentials")

    st.markdown(
        """
        <div class='feature-box'>
            <h3>What this demo highlights</h3>
            <ul>
                <li>Project progress cards for fast executive review</li>
                <li>Client-friendly update summaries with AI insights</li>
                <li>Financial visibility for budget and completion status</li>
                <li>Responsive display optimized for mobile presentation</li>
            </ul>
        </div>
        """,
        unsafe_allow_html=True,
    )
else:
    user = st.session_state.user
    st.sidebar.title(f"Hello, {user['name']}")
    st.sidebar.write(f"Role: {user['role']}")
    st.sidebar.write(f"Company: {user['company']}")
    if st.sidebar.button("Logout"):
        st.session_state.user = None
        st.experimental_rerun()

    projects = get_projects()
    total_projects = len(projects)
    avg_progress = round(sum(p["progress_percent"] for p in projects) / total_projects, 1) if total_projects else 0
    active_projects = sum(1 for p in projects if p["status"] != "Completed")
    completed_projects = sum(1 for p in projects if p["status"] == "Completed")

    st.markdown(
        """
        <style>
        .header-title {font-size: 2.8rem; font-weight: 700; margin-bottom: 0.3rem;}
        .header-subtitle {color: #64748b; margin-top: 0; margin-bottom: 1.5rem;}
        .metric-card {background: #ffffff; border-radius: 1rem; padding: 1.4rem; box-shadow: 0 18px 40px rgba(15, 23, 42, 0.12);}
        .metric-card h3 {margin: 0 0 0.6rem 0; font-size: 0.95rem; letter-spacing: 0.08em; text-transform: uppercase; color: #475569;}
        .metric-card h2 {margin: 0; font-size: 2.4rem; color: #0f172a;}
        .project-card {background: #ffffff; border-radius: 1.3rem; padding: 1.5rem; box-shadow: 0 18px 40px rgba(15, 23, 42, 0.08); margin-bottom: 1.6rem;}
        .project-card h2 {margin: 0 0 0.35rem 0; font-size: 1.55rem;}
        .project-card p {margin: 0.4rem 0; color: #475569;}
        .project-meta {margin-top: 0.8rem; color: #334155; font-size: 0.95rem;}
        .project-badge {display: inline-block; padding: 0.35rem 0.85rem; border-radius: 999px; font-size: 0.8rem; font-weight: 700; margin-right: 0.5rem;}
        .badge-progress {background: #e0f2fe; color: #0369a1;}
        .badge-status {background: #dcfce7; color: #166534;}
        .section-title {margin-top: 2rem; margin-bottom: 1rem; font-size: 1.75rem;}
        .customer-card {background: #0f172a; border-radius: 1.3rem; padding: 1.5rem; color: white; margin-bottom: 1.5rem;}
        .customer-card p {margin: 0.35rem 0;}
        .customer-highlight {color: #fbbf24;}
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(f"<h1 class='header-title'>Arthi Construction Control Center</h1><p class='header-subtitle'>A clean, customer-ready dashboard for project updates, financial visibility, and AI-powered insights.</p>", unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns([1, 1, 1, 1], gap="large")
    c1.markdown(f"<div class='metric-card'><h3>Total Projects</h3><h2>{total_projects}</h2></div>", unsafe_allow_html=True)
    c2.markdown(f"<div class='metric-card'><h3>Active</h3><h2>{active_projects}</h2></div>", unsafe_allow_html=True)
    c3.markdown(f"<div class='metric-card'><h3>Completed</h3><h2>{completed_projects}</h2></div>", unsafe_allow_html=True)
    c4.markdown(f"<div class='metric-card'><h3>Average Progress</h3><h2>{avg_progress}%</h2></div>", unsafe_allow_html=True)

    tab1, tab2, tab3 = st.tabs(["Dashboard", "Updates", "Customer View"])

    with tab1:
        st.markdown("<div class='section-title'>Project portfolio</div>", unsafe_allow_html=True)
        for project in projects:
            st.markdown(
                f"<div class='project-card'><h2>{project['name']}</h2><div class='project-meta'><span class='project-badge badge-progress'>{project['progress_percent']}% progress</span><span class='project-badge badge-status'>{project['status']}</span></div><p>{project['description']}</p><p class='project-meta'><strong>Tier:</strong> {project['tier']} | <strong>Location:</strong> {project['location']} | <strong>ETA:</strong> {project['expected_handover']} | <strong>Engineer:</strong> {project['engineer_name']}</p></div>",
                unsafe_allow_html=True,
            )
            st.progress(project['progress_percent'] / 100)
            st.info(project['ai_insight'])

    with tab2:
        st.markdown("<div class='section-title'>Customer-ready field updates</div>", unsafe_allow_html=True)
        for project in projects:
            st.markdown(f"<h3 style='margin-bottom:0.4rem;'>{project['name']}</h3>", unsafe_allow_html=True)
            updates = get_updates(project['id'])
            for update in updates:
                with st.expander(f"{update['title']} — {update['phase']}"):
                    st.write(update['message'])
                    st.caption(f"Updated on {update['created_at']}")
            st.divider()

    with tab3:
        st.markdown("<div class='section-title'>Client portal preview</div>", unsafe_allow_html=True)
        for project in projects:
            st.markdown(
                f"<div class='customer-card'><h2>{project['name']}</h2><p><strong>Client:</strong> {project['client_name']}</p><p><strong>Status:</strong> {project['status']}</p><p class='customer-highlight'><strong>Budget used:</strong> ₹{project['spent']:,} / ₹{project['budget']:,}</p><p><strong>Expected handover:</strong> {project['expected_handover']}</p></div>",
                unsafe_allow_html=True,
            )
            st.success(project['ai_insight'])
            st.divider()
