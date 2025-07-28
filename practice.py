import streamlit as st
import os
import json
import firebase_admin
from firebase_admin import credentials, firestore


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
        st.write( team["email"])
        st.write( team["members"])
        st.write( projects.get(team["team_name"], "Not Submitted"))

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
                st.success(" Score submitted!")

import streamlit as st
import openai

# ---------- OPENAI API ----------
# Replace this with your actual OpenAI key
openai.api_key = st.secrets["OPENAI_API_KEY"]

# ---------- Streamlit Section ----------
def mentorbot():
    st.title("🤖 MentorBot – Ask AI Your Hackathon Doubts")

    st.write("Stuck somewhere? Ask MentorBot for help with coding, ideas, or tech stack.")

    user_question = st.text_input("Enter your question:")

    if st.button("Get Answer") and user_question:
        with st.spinner("MentorBot is thinking..."):
            try:
                response = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "You are a helpful AI mentor for hackathon participants."},
                        {"role": "user", "content": user_question}
                    ]
                )
                answer = response['choices'][0]['message']['content']
                st.success(answer)
            except Exception as e:
                st.error(f"Error: {e}")

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