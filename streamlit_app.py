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
        .hero-card {background: linear-gradient(135deg, #0f172a, #111827); border-radius: 1rem; padding: 2rem; color: white;}
        .summary-box {background: white; border-radius: 1rem; padding: 1.5rem;}
        .credentials {background: #111827; color: white; border-radius: 1rem; padding: 1rem;}
        </style>
        <div class='hero-card'>
            <h1 style='margin-bottom:0.3rem; font-size: 3rem;'>Arthi Construction AI Demo</h1>
            <p style='color:#cbd5e1; font-size:1.05rem;'>A polished construction visibility experience for client presentations.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.sidebar.header("Demo Credentials")
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

    st.markdown("### What this demo shows")
    st.write("- AI-generated project insights")
    st.write("- Customer-friendly progress visibility")
    st.write("- Multi-tenant construction tracking")
    st.write("- Live-looking project updates")
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

    st.markdown(
        """
        <style>
        .header-row {display:flex; justify-content: space-between; align-items: center;}
        .header-title {font-size:2.5rem; font-weight:700;}
        .metric-card {background: white; border-radius: 1rem; padding: 1.5rem; box-shadow: 0 10px 30px rgba(15, 23, 42, 0.08);}
        .project-card {background: white; border-radius: 1rem; padding: 1.5rem; box-shadow: 0 10px 30px rgba(15, 23, 42, 0.08); margin-bottom: 1rem;}
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("<div class='header-row'><div><h1 class='header-title'>Arthi Construction Control Center</h1><p style='color:#475569;'>A presentation-ready overview for live construction tracking and customer communication.</p></div></div>", unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)
    col1.markdown(f"<div class='metric-card'><h3>Active Projects</h3><h2>{active_projects}</h2></div>", unsafe_allow_html=True)
    col2.markdown(f"<div class='metric-card'><h3>Average Progress</h3><h2>{avg_progress}%</h2></div>", unsafe_allow_html=True)
    col3.markdown("<div class='metric-card'><h3>AI Alerts</h3><h2>3 ready</h2></div>", unsafe_allow_html=True)

    tab1, tab2, tab3 = st.tabs(["Dashboard", "Updates", "Customer View"])

    with tab1:
        st.subheader("Project portfolio")
        for project in projects:
            st.markdown(f"<div class='project-card'><h2>{project['name']}</h2><p>{project['description']}</p>", unsafe_allow_html=True)
            st.progress(project['progress_percent'] / 100)
            st.write(f"**{project['progress_percent']}% complete**")
            st.write(f"**Tier:** {project['tier']}  •  **Location:** {project['location']}  •  **ETA:** {project['expected_handover']}")
            st.info(project['ai_insight'])
            st.markdown("</div>", unsafe_allow_html=True)

    with tab2:
        st.subheader("Field updates generated for customers")
        for project in projects:
            st.markdown(f"### {project['name']}")
            updates = get_updates(project['id'])
            for update in updates:
                with st.expander(update['title']):
                    st.write(update['message'])
                    st.caption(f"Phase: {update['phase']} | {update['created_at']}")
            st.divider()

    with tab3:
        st.subheader("Customer portal experience")
        for project in projects:
            st.markdown(f"<div class='project-card'><h2>{project['name']}</h2><p>Client: {project['client_name']}</p><p>Status: {project['status']}</p><p>Budget used: ₹{project['spent']:,} / ₹{project['budget']:,}</p><p>Expected handover: {project['expected_handover']}</p></div>", unsafe_allow_html=True)
            st.success(project['ai_insight'])
            st.divider()