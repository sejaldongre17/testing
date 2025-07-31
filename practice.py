import streamlit as st
import os
import json
import firebase_admin
from firebase_admin import credentials, firestore
import requests
import time

# ---------------- SETUP ----------------
DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)
PROBLEM_FILE = os.path.join(DATA_DIR, "problems.json")

def load_json(path):
    try:
        with open(path, "r") as f:
            return json.load(f)
    except:
        return []

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

if not firebase_admin._apps:
    key_dict = json.loads(st.secrets["FIREBASE_KEY"])
    cred = credentials.Certificate(key_dict)
    firebase_admin.initialize_app(cred)
db = firestore.client()

AUTHOR_PASSWORD = "author@123"

# ---------------- STUDENT & AUTHOR HOME ----------------
def home(user_is_author=False):
    st.title("🚀 HackaAIverse - A One Day Hackathon")

    st.header("📌 Problem Statements")
    problems = load_json(PROBLEM_FILE)
    if not problems:
        st.info("No problem statements yet.")
    else:
        for i, p in enumerate(problems):
            st.markdown(f"**{i+1}. {p['title']}**")
            st.write(p["description"])

    if user_is_author:
        st.header("➕ Add Problem Statement")
        with st.form("add_problem_json"):
            title = st.text_input("Title")
            desc = st.text_area("Description")
            if st.form_submit_button("Add Problem"):
                problems.append({"title": title, "description": desc})
                save_json(PROBLEM_FILE, problems)
                st.success("✅ Problem added!")

    st.header("📝 Register Team")
    with st.form("register_team"):
        team_name = st.text_input("Team Name")
        members = st.text_area("Members")
        email = st.text_input("Email")
        if st.form_submit_button("Register"):
            db.collection("teams").document(team_name).set({
                "team_name": team_name,
                "members": members,
                "email": email
            })
            st.success("✅ Team registered!")

    st.header("🔗 Submit Project Link")
    with st.form("submit_project"):
        team = st.text_input("Registered Team Name")
        link = st.text_input("GitHub/Drive Project Link")
        if st.form_submit_button("Submit"):
            db.collection("projects").document(team).set({
                "team": team,
                "project_link": link
            })
            st.success("✅ Project link submitted!")

# ---------------- JUDGE PANEL (MANUAL) ----------------
def judge_panel():
    st.title("👨‍⚖️ Judge Panel (Manual)")

    password = st.text_input("Enter Author Password", type="password")
    if password != AUTHOR_PASSWORD:
        st.warning("❌ Access Denied")
        return

    st.success("✅ Access Granted")

    teams = db.collection("teams").stream()
    projects = {p.id: p.to_dict()["project_link"] for p in db.collection("projects").stream()}

    for t in teams:
        team = t.to_dict()
        st.subheader(team["team_name"])
        st.write(team["email"])
        st.write(team["members"])
        st.write(projects.get(team["team_name"], "Not Submitted"))

        with st.form(f"score_{team['team_name']}"):
            usefulness = st.slider("Usefulness", 1, 10)
            creativity = st.slider("Creativity", 1, 10)
            teamwork = st.slider("Teamwork", 1, 10)
            tech_stack = st.slider("Tech Stack", 1, 10)
            clarity = st.slider("Clarity", 1, 10)
            if st.form_submit_button("Submit Score"):
                db.collection("scores").add({
                    "team": team["team_name"],
                    "scores": {
                        "usefulness": usefulness,
                        "creativity": creativity,
                        "teamwork": teamwork,
                        "tech_stack": tech_stack,
                        "clarity": clarity
                    }
                })
                st.success("✅ Score submitted!")

# ---------------- AI JUDGING BOT ----------------
def judging_bot():
    st.title("🤖 JudgingBot - AI-Based Scoring")

    projects = db.collection("projects").stream()

    for project in projects:
        data = project.to_dict()
        team_id = project.id
        team_name = data.get("team")
        project_link = data.get("project_link")

        st.subheader(f"Team: {team_name}")
        st.write(f"🔗 Link: {project_link}")

        if st.button(f"Judge {team_name}"):
            prompt = f"""
            Evaluate the following project submitted at {project_link}.
            Score it (1-10) on:
            - Usefulness
            - Creativity
            - Teamwork
            - Tech Stack
            - Clarity
            Return JSON like:
            {{
              "usefulness": 8,
              "creativity": 9,
              "teamwork": 7,
              "tech_stack": 8,
              "clarity": 9,
              "total_score": 41
            }}
            """

            headers = {
                "Authorization": f"Bearer {st.secrets['OPENROUTER_API_KEY']}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": "mixtral-8x7b-32768",
                "messages": [{"role": "user", "content": prompt}]
            }

            res = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload)
            result = res.json()

            try:
                content = result["choices"][0]["message"]["content"]
                scores = json.loads(content)
                db.collection("scores").document(team_id).set(scores)
                st.success(f"✅ Judged! Total: {scores['total_score']}")
            except:
                st.error("❌ AI Error")
                st.json(result)

# ---------------- MENTOR BOT ----------------
def mentor_bot():
    st.title("🎓 MentorBot - Ask Me Anything")

    query = st.text_input("Ask a question about the hackathon")

    if st.button("Ask") and query:
        headers = {
            "Authorization": f"Bearer {st.secrets['OPENROUTER_API_KEY']}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "mixtral-8x7b-32768",
            "messages": [{"role": "user", "content": f"You are a mentor at a hackathon. Answer this: {query}"}]
        }

        res = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload)
        answer = res.json()["choices"][0]["message"]["content"]
        st.success(answer)

# ---------------- REMINDER BOT ----------------
def reminder_bot():
    st.title("⏰ ReminderBot - Event Alerts")

    reminders = [
        "🚨 Project Submission closes at 6 PM!",
        "🎯 Judging starts at 7 PM!",
        "🎉 Closing ceremony at 8 PM!",
    ]

    for r in reminders:
        st.info(r)
        time.sleep(1)

# ---------------- PAGE NAVIGATION ----------------
page = st.sidebar.selectbox("📂 Select Page", [
    "Home (Student/Author)", "Judge Panel (Manual)",
    "AI Agents - JudgingBot", "AI Agents - MentorBot", "AI Agents - ReminderBot"
])

if page == "Home (Student/Author)":
    user_type = st.selectbox("Who are you?", ["Student", "Author"])
    if user_type == "Author":
        pwd = st.text_input("Author Password", type="password")
        home(user_is_author=(pwd == AUTHOR_PASSWORD))
    else:
        home()

elif page == "Judge Panel (Manual)":
    judge_panel()

elif page == "AI Agents - JudgingBot":
    judging_bot()

elif page == "AI Agents - MentorBot":
    mentor_bot()

elif page == "AI Agents - ReminderBot":
    reminder_bot()
