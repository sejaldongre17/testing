import streamlit as st
import os
import json
import firebase_admin
from firebase_admin import credentials, firestore
import requests  # ✅ Required for Groq
# ------------------------------⬇️ ADD THIS FUNCTION BELOW⬇️------------------------------


def judge_with_groq(project_description, team_name):
    GROQ_API_KEY = st.secrets["groq"]["key"]

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    prompt = f"""
You are an expert Hackathon Judge. Based on this student project description, rate the project from 1 to 10 on:
- Usefulness
- Creativity
- Tech Stack
- Clarity

Respond ONLY in JSON format like:
{{
  "usefulness": 7,
  "creativity": 8,
  "tech_stack": 6,
  "clarity": 9
}}

Project Description:
\"\"\"
{project_description[:3000]}
\"\"\"
    """

    payload = {
        "model": "mixtral-8x7b-32768",
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.5
    }

    response = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers=headers,
        json=payload
    )

    if response.status_code == 200:
        try:
            result = response.json()["choices"][0]["message"]["content"]
            scores = json.loads(result)
            db.collection("scores").add({
                "team": team_name,
                "scores": scores,
                "judged_by": "AI-Groq"
            })
            return scores
        except Exception as e:
            st.error(f"Failed to parse AI response: {str(e)}")
            return None
    else:
        st.error(f"Groq API Error {response.status_code}: {response.text}")
        return None


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


def home(user_is_author=False):
    st.title(" HackaAIverse - A one day Hackathon for Students")

    st.header(" Problem Statements (from JSON)")
    problems = load_json(PROBLEM_FILE)
    if not problems:
        st.info("No problem statements available yet.")
    else:
        for i, p in enumerate(problems):
            st.markdown(f"**{i+1}. {p['title']}**")
            st.write(p["description"])

    if user_is_author:
        st.header(" Add Problem Statement (JSON)")
        with st.form("add_problem_json"):
            title = st.text_input("Title")
            desc = st.text_area("Description")
            if st.form_submit_button("Add Problem"):
                problems.append({"title": title, "description": desc})
                save_json(PROBLEM_FILE, problems)
                st.success(" Problem added to JSON!")

    st.header(" Register Team")
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
            st.success(" Team registered!")

    
    st.header(" Submit Project Link")
    with st.form("submit_project"):
        team = st.text_input("Registered Team Name")
        link = st.text_input("GitHub/Drive Project Link")
        if st.form_submit_button("Submit"):
            db.collection("projects").document(team).set({
                "team": team,
                "project_link": link
            })
            st.success(" Project link submitted!")


def judge_panel():
    st.title(" Judge Panel (Author Only)")

    password = st.text_input("Enter Author Password", type="password")
    if password != AUTHOR_PASSWORD:
        st.warning(" Access Denied")
        return

    st.success(" Access Granted")

    teams = db.collection("teams").stream()
    projects = {p.id: p.to_dict()["project_link"] for p in db.collection("projects").stream()}

    for t in teams:
        team = t.to_dict()
        st.subheader(team["team_name"])
        st.write(team["email"])
        st.write(team["members"])
        st.write(projects.get(team["team_name"], "Not Submitted"))

        if st.button(f"Judge with AI: {team['team_name']}"):
            project_link = projects.get(team["team_name"])
            if not project_link:
                st.warning("Project not submitted yet.")
                continue

            try:
                if "github.com" in project_link:
                    # Try to fetch README.md
                    raw_url = project_link.replace("github.com", "raw.githubusercontent.com").replace("/blob/", "/") + "/README.md"
                    res = requests.get(raw_url)
                    content = res.text if res.status_code == 200 else "No README content found."
                else:
                    content = "Project description not available from this link."

                with st.spinner("AI judging in progress..."):
                    scores = judge_with_groq(content, team["team_name"])
                    if scores:
                        st.success("AI Judging Complete!")
                        st.json(scores)
            except Exception as e:
                st.error(f"Error during judging: {str(e)}")


page = st.sidebar.radio("Navigate", [" Student/Author View", " Judge Panel"])

if page == " Student/Author View":
    user_type = st.selectbox("Who are you?", ["Student", "Author"])
    if user_type == "Author":
        pwd = st.text_input("Enter Author Password", type="password")
        home(user_is_author=(pwd == AUTHOR_PASSWORD))
    else:
        home()
elif page == " Judge Panel":
    judge_panel()