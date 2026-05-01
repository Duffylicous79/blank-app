import sqlite3
from datetime import datetime
from pathlib import Path

import streamlit as st

DB_PATH = Path("dev_log.db")


def connect_db():
    return sqlite3.connect(DB_PATH, check_same_thread=False)


def setup_db():
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS dev_log_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            text TEXT NOT NULL,
            category TEXT NOT NULL DEFAULT 'General',
            status TEXT NOT NULL DEFAULT 'todo',
            created_at TEXT NOT NULL
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS app_settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
        """
    )
    conn.commit()
    return conn


def seed_data(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM dev_log_items")
    count = cursor.fetchone()[0]

    if count == 0:
        starter_items = [
            ("Players should no longer encounter non-damageable mobs.", "Combat", "fixed"),
            ("Boost timers have been fixed.", "Boosts", "fixed"),
            ("Map sometimes struggles to load when joining, even when the level requirement is met.", "Map", "todo"),
            ("Redeem system is not giving the correct resources.", "Redeem", "todo"),
            ("APK version currently cannot use portrait mode.", "APK", "todo"),
        ]
        now = datetime.now().isoformat(timespec="seconds")
        cursor.executemany(
            "INSERT INTO dev_log_items (text, category, status, created_at) VALUES (?, ?, ?, ?)",
            [(text, category, status, now) for text, category, status in starter_items],
        )

    cursor.execute(
        "INSERT OR IGNORE INTO app_settings (key, value) VALUES (?, ?)",
        ("game_status", "Game now in Alpha"),
    )
    conn.commit()


def get_setting(conn, key, default=""):
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM app_settings WHERE key = ?", (key,))
    row = cursor.fetchone()
    return row[0] if row else default


def set_setting(conn, key, value):
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO app_settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (key, value),
    )
    conn.commit()


def get_items(conn, status_filter="all"):
    cursor = conn.cursor()
    if status_filter == "all":
        cursor.execute("SELECT id, text, category, status, created_at FROM dev_log_items ORDER BY id DESC")
    else:
        cursor.execute(
            "SELECT id, text, category, status, created_at FROM dev_log_items WHERE status = ? ORDER BY id DESC",
            (status_filter,),
        )
    return cursor.fetchall()


def add_item(conn, text, category):
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO dev_log_items (text, category, status, created_at) VALUES (?, ?, ?, ?)",
        (text, category or "General", "todo", datetime.now().isoformat(timespec="seconds")),
    )
    conn.commit()


def toggle_item(conn, item_id, current_status):
    next_status = "fixed" if current_status == "todo" else "todo"
    cursor = conn.cursor()
    cursor.execute("UPDATE dev_log_items SET status = ? WHERE id = ?", (next_status, item_id))
    conn.commit()


def delete_item(conn, item_id):
    cursor = conn.cursor()
    cursor.execute("DELETE FROM dev_log_items WHERE id = ?", (item_id,))
    conn.commit()


def count_items(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT status, COUNT(*) FROM dev_log_items GROUP BY status")
    counts = {"todo": 0, "fixed": 0}
    for status, count in cursor.fetchall():
        counts[status] = count
    counts["all"] = counts["todo"] + counts["fixed"]
    return counts


st.set_page_config(page_title="Shared Dev Log", page_icon="🛠️", layout="wide")

conn = setup_db()
seed_data(conn)

st.title("🛠️ Shared Dev Log")
st.caption("A simple tracker for your game updates, bugs, fixes, and alpha tasks.")

status_value = get_setting(conn, "game_status", "Game now in Alpha")
new_status = st.text_input("Game status", value=status_value)
if new_status != status_value:
    set_setting(conn, "game_status", new_status)
    st.success("Game status updated.")

counts = count_items(conn)
col1, col2, col3 = st.columns(3)
col1.metric("All", counts["all"])
col2.metric("Fixed", counts["fixed"])
col3.metric("To Work On", counts["todo"])

st.divider()

with st.form("add_item_form", clear_on_submit=True):
    st.subheader("Add new task")
    text = st.text_input("Task, bug, or fix")
    category = st.text_input("Category", value="General")
    submitted = st.form_submit_button("Add")

    if submitted:
        if text.strip():
            add_item(conn, text.strip(), category.strip())
            st.success("Added.")
            st.rerun()
        else:
            st.warning("Write something first.")

filter_label = st.radio(
    "Show",
    ["All", "To Work On", "Fixed"],
    horizontal=True,
)

filter_map = {
    "All": "all",
    "To Work On": "todo",
    "Fixed": "fixed",
}

items = get_items(conn, filter_map[filter_label])

st.subheader(filter_label)

if not items:
    st.info("No items here yet.")

for item_id, item_text, category, status, created_at in items:
    with st.container(border=True):
        top_col, button_col, delete_col = st.columns([7, 1.5, 1])

        with top_col:
            badge = "✅ Fixed" if status == "fixed" else "🟠 To Work On"
            st.markdown(f"**{badge}** · `{category}`")
            st.write(item_text)
            st.caption(f"Created: {created_at}")

        with button_col:
            if st.button("Toggle", key=f"toggle-{item_id}"):
                toggle_item(conn, item_id, status)
                st.rerun()

        with delete_col:
            if st.button("Delete", key=f"delete-{item_id}"):
                delete_item(conn, item_id)
                st.rerun()

st.divider()
st.info(
    "Valfor = gay, "
    "LQS when."
)
