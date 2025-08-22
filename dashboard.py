# app/admin/dashboard.py

import pandas as pd
import streamlit as st
import os
import plotly.express as px
import re
from datetime import datetime, date
import json
import helper.summarizer as summarizer
import uuid

# run summarizer (keeps existing behaviour)
summarizer.main()
LOG_FILE = "data\\bot.log"
SUMMARY_PATH = "data\\summary_log.jsonl"

st.set_page_config(page_title="ILLORA_RETREATS – Admin Console", layout="wide")
st.title("🏨 Illora Retreats – Concierge AI Admin Dashboard")

# --- Helpers ---
def load_json(path, default):
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(default, f, indent=2)
    with open(path, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except:
            return default

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def ensure_csv(path, cols):
    if not os.path.exists(path):
        pd.DataFrame(columns=cols).to_csv(path, index=False)
    return pd.read_csv(path)

# --- Data Sources ---
QA_CSV = "data\\qa_pairs.csv"
MENU_FILE = "services\\menu.json"
CAMPAIGNS_FILE = "data\\campaigns.json"

# --- Tabs ---
tabs = st.tabs(["📊 Analytics", "💬 Q&A Manager", "🏷️ Menu Manager", "📢 Campaigns Manager", "✅ Do's & ❌ Don'ts Manager"])

# ======================================================
# 📊 ANALYTICS TAB
# ======================================================
with tabs[0]:
    if not os.path.exists(LOG_FILE):
        st.warning("No logs found yet.")
        st.stop()

    # --- Parse logs ---
    log_lines = []
    with open(LOG_FILE, "r", encoding="ISO-8859-1") as f:
        for line in f:
            parts = [part.strip() for part in line.strip().split("|")]
            if len(parts) >= 8:
                timestamp = parts[0]
                source = parts[3]
                session_id = parts[4]
                user_input = parts[5]
                response = parts[6]
                guest_type = parts[7]
                intent_match = re.search(r"Intent: (.+)", line)
                intent = intent_match.group(1) if intent_match else "Unknown"
                log_lines.append([timestamp, source, session_id, user_input, response, intent, guest_type])

    df = pd.DataFrame(
        log_lines,
        columns=["Timestamp", "Source", "Session ID", "User Input", "Response", "Intent", "Guest Type"],
    )
    df["Timestamp"] = pd.to_datetime(df["Timestamp"], errors="coerce")
    df["Date"] = df["Timestamp"].dt.date

    # --- Sidebar filters ---
    st.sidebar.header("🔍 Filter Analytics")
    source_filter = st.sidebar.selectbox("📱 Channel", ["All"] + sorted(df["Source"].unique().tolist()))
    intent_filter = st.sidebar.selectbox("🎯 Intent", ["All"] + sorted(df["Intent"].unique().tolist()))
    guest_filter = st.sidebar.selectbox("🏷️ Guest Type", ["All", "Guest", "Non-Guest"])

    filtered_df = df.copy()
    if source_filter != "All":
        filtered_df = filtered_df[filtered_df["Source"] == source_filter]
    if intent_filter != "All":
        filtered_df = filtered_df[filtered_df["Intent"] == intent_filter]
    if guest_filter != "All":
        filtered_df = filtered_df[filtered_df["Guest Type"].str.lower() == guest_filter.lower()]

    # KPIs
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("🗨️ Total Interactions", len(filtered_df))
    col2.metric("👥 Unique Sessions", filtered_df["Session ID"].nunique())
    col3.metric("🔍 Unique Intents", filtered_df["Intent"].nunique())
    col4.metric("🏷️ Guest Type", guest_filter if guest_filter != "All" else "All Types")

    st.markdown("---")

    # Graphs
    st.subheader("Guest vs Non-Guest Breakdown")
    guest_counts = df["Guest Type"].value_counts().reset_index()
    guest_counts.columns = ["Guest Type", "Messages"]
    st.plotly_chart(px.pie(guest_counts, names="Guest Type", values="Messages"), use_container_width=True)

    st.subheader("Channel Distribution")
    source_counts = filtered_df["Source"].value_counts().reset_index()
    source_counts.columns = ["Channel", "Messages"]
    st.plotly_chart(px.pie(source_counts, names="Channel", values="Messages"), use_container_width=True)

    st.subheader("Daily Interaction Volume")
    daily = filtered_df.groupby("Date").size().reset_index(name="Messages")
    st.plotly_chart(px.line(daily, x="Date", y="Messages", markers=True), use_container_width=True)

    st.subheader("Guest Needs Breakdown")
    intent_counts = filtered_df["Intent"].value_counts().reset_index()
    intent_counts.columns = ["Intent", "Count"]
    st.plotly_chart(px.bar(intent_counts, x="Intent", y="Count", color="Intent"), use_container_width=True)

    st.subheader("Engagement by Session")
    session_counts = filtered_df["Session ID"].value_counts().reset_index()
    session_counts.columns = ["Session ID", "Messages"]
    st.plotly_chart(px.bar(session_counts, x="Session ID", y="Messages"), use_container_width=True)

    st.subheader("📜 Guest Interaction Log")
    st.dataframe(filtered_df)

    st.download_button("📥 Download Logs as CSV", filtered_df.to_csv(index=False), file_name="ILLORA_logs.csv")

    st.subheader("🧠 Guest Session Summaries")
    if os.path.exists(SUMMARY_PATH):
        summaries = []
        with open(SUMMARY_PATH, "r", encoding="ISO-8859-1") as f:
            for line in f:
                try:
                    summaries.append(json.loads(line.strip()))
                except:
                    continue
        if summaries:
            summary_df = pd.DataFrame(summaries)
            for _, row in summary_df.iterrows():
                with st.expander(f"Session: {row['session_id']}"):
                    st.write("📝", row["summary"])
                    st.write("📧", row["follow_up_email"])

# ======================================================
# 💬 Q&A MANAGER TAB
# ======================================================
with tabs[1]:
    st.header("💬 Q&A Manager")
    qa_df = ensure_csv('data\\qa_pairs.csv', ["question", "answer"])
    st.dataframe(qa_df, use_container_width=True)

    with st.form("addqa", clear_on_submit=True):
        q = st.text_input("Question")
        a = st.text_area("Answer")
        if st.form_submit_button("➕ Add Q&A"):
            qa_df = qa_df.append({"question": q, "answer": a}, ignore_index=True)
            qa_df.to_csv(QA_CSV, index=False)
            st.success("Q&A added!")

# ======================================================
# 🏷️ MENU MANAGER TAB
# ======================================================
with tabs[2]:
    st.header("🏷️ Menu Manager")
    default_menu = {"add_ons": {}, "rooms": {}, "complimentary": {}}
    menu = load_json(MENU_FILE, default_menu)

    for cat, items in menu.items():
        with st.expander(f"{cat.title()}"):
            if isinstance(items, dict):
                df_items = pd.DataFrame([{"key": k, "price": v} for k, v in items.items()])
                st.dataframe(df_items)
            elif isinstance(items, list):
                st.dataframe(pd.DataFrame(items))
            else:
                st.info("Empty category")

# ======================================================
# 📢 CAMPAIGNS MANAGER TAB
# ======================================================
with tabs[3]:
    st.header("📢 Campaigns Manager")
    campaigns = load_json(CAMPAIGNS_FILE, [])

    if campaigns:
        st.dataframe(pd.DataFrame(campaigns), use_container_width=True)
    else:
        st.info("No campaigns yet.")

    st.markdown("### ➕ Create New Campaign / Upsell")
    with st.form("create_campaign", clear_on_submit=True):
        name = st.text_input("Campaign Name")
        desc = st.text_area("Description")
        discount_type = st.selectbox("Discount Type", ["percent", "fixed"])
        discount_value = st.number_input("Discount Value", min_value=0.0, value=10.0, step=1.0)
        start_date = st.date_input("Start Date", value=date.today())
        end_date = st.date_input("End Date", value=date.today())
        active = st.checkbox("Active", value=True)

        if st.form_submit_button("Create Campaign"):
            camp_id = str(uuid.uuid4())
            new_campaign = {
                "id": camp_id,
                "name": name,
                "description": desc,
                "discount_type": discount_type,
                "discount_value": discount_value,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "active": active,
                "created_at": datetime.utcnow().isoformat()
            }
            campaigns.append(new_campaign)
            save_json(CAMPAIGNS_FILE, campaigns)
            st.success(f"Campaign '{name}' created!")


# ======================================================
# ✅ DO'S & ❌ DON'TS MANAGER TAB
# ======================================================
with tabs[4]:
    st.header("✅ Do's & ❌ Don'ts Manager")

    DOSDONTS_FILE = 'data\\dos_donts.json'    
    # Load existing instructions
    dos_donts = load_json(DOSDONTS_FILE, [])

    if dos_donts:
        st.dataframe(pd.DataFrame(dos_donts), use_container_width=True)
    else:
        st.info("No instructions added yet.")

    st.markdown("### ➕ Add New Instruction")
    with st.form("add_dos_donts", clear_on_submit=True):
        do_text = st.text_area("✅ Do (Instruction to say/encourage)", "")
        dont_text = st.text_area("❌ Don't (Instruction to avoid)", "")
        if st.form_submit_button("Add Instruction"):
            if do_text.strip() or dont_text.strip():
                new_entry = {"do": do_text.strip(), "dont": dont_text.strip()}
                dos_donts.append(new_entry)
                save_json(DOSDONTS_FILE, dos_donts)
                st.success("Instruction added successfully!")
            else:
                st.warning("Please fill at least one field.")


##########################################################################