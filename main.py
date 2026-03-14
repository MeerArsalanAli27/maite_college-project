# maite_chain.py
import datetime
from typing import List, Dict, Any
from langchain_core.chat_history import InMemoryChatMessageHistory

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.chat_history import BaseChatMessageHistory

# from langchain import ChatMessageHistory
from langchain_core.runnables import RunnableWithMessageHistory
# import google.generativeai as genai
from langchain_google_genai import ChatGoogleGenerativeAI

# configure Gemini API key (env var recommended)
import os
# genai.configure(api_key="AIzaSyCBQdxn4gXP7TVOj0KOhoK0pISo7iVG3FQ")

# In-memory store keyed by user/session id (Streamlit will use session_state key)
_CHAT_STORES: dict[str, BaseChatMessageHistory] = {}


# def get_history_store(session_id: str) -> BaseChatMessageHistory:
#     if session_id not in _CHAT_STORES:
#         _CHAT_STORES[session_id] = BaseChatMessageHistory()
#     return _CHAT_STORES[session_id]

def get_history_store(session_id):
    if session_id not in _CHAT_STORES:
        # Use the actual implementation here
        _CHAT_STORES[session_id] = InMemoryChatMessageHistory() 
    return _CHAT_STORES[session_id]


SYSTEM_PROMPT = """
You are Maite, an AI personal scheduler.

Your ONLY role:
- Help users turn tasks into realistic schedules.
- Ask clarifying questions instead of guessing.
- Use a friendly, calm, encouraging tone.
- Never act as a therapist, general assistant, or search engine.

You MUST:
- Focus only on time management, productivity, and scheduling.
- Distinguish between fixed events (exact times) and flexible tasks.
- Consider user personality, energy patterns, and preferences when scheduling.
- Avoid rigid, minute-by-minute micromanagement unless requested.

When you build or update schedules, use this 4-column table:

| Task | Scheduled Time | Helpful Keywords | ✓ |

Use Markdown tables in your answers, and keep them readable.
When information is missing (duration, fixed vs flexible, preference), ask:
- “How long should this task take?”
- “Is this flexible or fixed?”
- “Do you prefer earlier or later in the day?”

Respect privacy:
- Never claim to read calendars or apps unless user explicitly says they connected them.
- Only use data the user provided in the conversation.

Always sound like: "A calm, smart planner that helps you move forward."
"""

prompt = ChatPromptTemplate.from_messages(
    [
        ("system", SYSTEM_PROMPT),
        MessagesPlaceholder("history"),
        ("human", "{input}"),
    ]
)



llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",  # or any other Gemini chat model
    temperature=0.4,
    api_key="AIzaSyCBQdxn4gXP7TVOj0KOhoK0pISo7iVG3FQ"
)


maite_chain = prompt | llm


def get_maite_chain_with_memory() -> RunnableWithMessageHistory:
    """
    Wraps the chain with LangChain's message history so conversation context is preserved.
    """
    return RunnableWithMessageHistory(
        maite_chain,
        get_history_store,
        input_messages_key="input",
        history_messages_key="history",
    )


def call_maite(session_id: str, user_input: str) -> str:
    chain = get_maite_chain_with_memory()
    res = chain.invoke(
        {"input": user_input},
        config={"configurable": {"session_id": session_id}},
    )
    return res.content


















# maite_app.py
import datetime
from typing import List, Dict, Any

import streamlit as st



# ---------- PAGE CONFIG ----------
st.set_page_config(
    page_title="Maite – AI Scheduler",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ---------- DARK THEME OVERRIDE ----------
# You can also set theme in .streamlit/config.toml, but this keeps the file self-contained.
DARK_CSS = """
<style>
body {
    background: radial-gradient(circle at top, #0f172a 0%, #020617 40%, #000000 100%);
    color: #f9fafb;
    font-family: system-ui, -apple-system, BlinkMacSystemFont, "SF Pro Text", sans-serif;
}

/* Main app background */
[data-testid="stAppViewContainer"] {
    background: radial-gradient(circle at top, #020617 0%, #020617 30%, #000000 100%);
}

/* Sidebar */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #020617 0%, #020617 40%, #020617 70%, #000000 100%);
    border-right: 1px solid rgba(148, 163, 184, 0.25);
    box-shadow: 0 0 30px rgba(15, 23, 42, 0.9);
}

/* Global text + links */
body, .stMarkdown, .stText, .stCaption, .stWrite {
    color: #f9fafb !important;
}
a {
    color: #38bdf8;
    text-decoration: none;
}
a:hover {
    text-shadow: 0 0 8px rgba(56, 189, 248, 0.9);
}

/* Make all widget labels & text white */
label, span, p, div, input, textarea {
    color: #f9fafb !important;
}

/* Main container spacing */
.block-container {
    padding-top: 1.5rem;
}

/* User chat bubble – neon cyan */
.maite-chat-bubble-user {
    background: radial-gradient(circle at top left, #22d3ee 0%, #0f172a 45%, #020617 100%);
    padding: 0.7rem 0.9rem;
    border-radius: 0.9rem;
    margin-bottom: 0.35rem;
    border: 1px solid rgba(56, 189, 248, 0.7);
    box-shadow:
        0 0 18px rgba(56, 189, 248, 0.4),
        0 0 3px rgba(15, 23, 42, 1);
}

/* Assistant chat bubble – purple/indigo glow */
.maite-chat-bubble-assistant {
    background: radial-gradient(circle at top right, #4c1d95 0%, #111827 45%, #020617 100%);
    padding: 0.7rem 0.9rem;
    border-radius: 0.9rem;
    margin-bottom: 0.35rem;
    border: 1px solid rgba(129, 140, 248, 0.7);
    box-shadow:
        0 0 18px rgba(129, 140, 248, 0.35),
        0 0 3px rgba(15, 23, 42, 1);
}

/* Headings – subtle glow */
h1, h2, h3, h4 {
    letter-spacing: 0.03em;
    text-transform: none;
    color: #ffffff !important;
    text-shadow:
        0 0 10px rgba(59, 130, 246, 0.5),
        0 0 20px rgba(56, 189, 248, 0.35);
}

/* Tags – pill style, neon borders */
.maite-tag {
    padding: 0.15rem 0.6rem;
    border-radius: 999px;
    font-size: 0.7rem;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    border: 1px solid rgba(148, 163, 184, 0.5);
    color: #f9fafb !important;
}

/* Scheduled: indigo/cyan */
.maite-tag-scheduled {
    background: rgba(15, 23, 42, 0.9);
    color: #f9fafb;
    border-color: rgba(56, 189, 248, 0.7);
    box-shadow: 0 0 10px rgba(56, 189, 248, 0.35);
}

/* Completed: emerald */
.maite-tag-completed {
    background: rgba(6, 78, 59, 0.9);
    color: #ecfdf5;
    border-color: rgba(45, 212, 191, 0.7);
    box-shadow: 0 0 10px rgba(16, 185, 129, 0.55);
}

/* Cancelled: red */
.maite-tag-cancelled {
    background: rgba(127, 29, 29, 0.95);
    color: #fee2e2;
    border-color: rgba(248, 113, 113, 0.9);
    box-shadow: 0 0 10px rgba(248, 113, 113, 0.55);
}

/* Schedule table text */
.css-1dp5vir, .css-1q7ov7n, .css-1kyxreq {
    color: #f9fafb !important;
}

/* Buttons – glowing, pill-like */
.stButton > button {
    border-radius: 999px;
    border: 1px solid rgba(56, 189, 248, 0.8);
    background: radial-gradient(circle at top, #0f172a 0%, #020617 100%);
    color: #f9fafb !important;
    padding: 0.4rem 0.9rem;
    font-size: 0.85rem;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    box-shadow:
        0 0 12px rgba(56, 189, 248, 0.45),
        0 0 2px rgba(15, 23, 42, 1);
    transition: all 0.18s ease-out;
}
.stButton > button:hover {
    transform: translateY(-1px) scale(1.02);
    box-shadow:
        0 0 16px rgba(56, 189, 248, 0.75),
        0 0 2px rgba(15, 23, 42, 1);
    border-color: rgba(129, 140, 248, 0.9);
}

/* Chat input – subtle inner glow */
[data-testid="stChatInput"] textarea {
    background-color: #020617 !important;
    border-radius: 0.75rem !important;
    border: 1px solid rgba(51, 65, 85, 0.9) !important;
    color: #f9fafb !important;
    box-shadow: 0 0 14px rgba(15, 23, 42, 0.9);
}

/* Chat input placeholder text white */
[data-testid="stChatInput"] textarea::placeholder {
    color: #ffffff !important;
    opacity: 1 !important;
}

/* Generic input + textarea placeholders white */
input::placeholder,
textarea::placeholder {
    color: #ffffff !important;
    opacity: 1 !important;
}

/* Scrollbar – thin neon */
::-webkit-scrollbar {
    width: 8px;
}
::-webkit-scrollbar-track {
    background: #020617;
}
::-webkit-scrollbar-thumb {
    background: linear-gradient(180deg, #22d3ee, #6366f1);
    border-radius: 999px;
}
::-webkit-scrollbar-thumb:hover {
    background: linear-gradient(180deg, #38bdf8, #818cf8);
}
</style>
"""


st.markdown(DARK_CSS, unsafe_allow_html=True)

# ---------- SESSION STATE ----------
if "messages" not in st.session_state:
    st.session_state.messages: List[Dict[str, str]] = [
        {
            "role": "assistant",
            "content": (
                "Hi, I’m Maite, your scheduling companion.\n\n"
                "To get started, tell me a few **personality keywords** about how you work "
                "(for example: early bird, procrastinator, deep-focus worker, easily distracted)."
            ),
        }
    ]

if "schedule_rows" not in st.session_state:
    # Each row: {id, task, time, keywords, done, kind ('fixed'|'flexible')}
    st.session_state.schedule_rows: List[Dict[str, Any]] = []

if "events" not in st.session_state:
    # Events panel items: {id, title, time, status}
    st.session_state.events: List[Dict[str, Any]] = []

if "stats" not in st.session_state:
    st.session_state.stats = {
        "completed": 0,
        "total": 0,
        "seven_day_history": [],  # later for summaries
    }

SESSION_ID = "streamlit_maite_demo"  # in production, use user id or a random uuid


# ---------- HELPERS ----------
def add_schedule_row(task: str, time_str: str, keywords: str, kind: str = "flexible"):
    row_id = f"row-{len(st.session_state.schedule_rows)+1}"
    st.session_state.schedule_rows.append(
        {
            "id": row_id,
            "task": task,
            "time": time_str,
            "keywords": keywords,
            "done": False,
            "kind": kind,
        }
    )
    st.session_state.events.append(
        {
            "id": row_id,
            "title": task,
            "time": time_str,
            "status": "scheduled",
        }
    )
    st.session_state.stats["total"] += 1


def set_row_done(row_id: str, value: bool):
    for row in st.session_state.schedule_rows:
        if row["id"] == row_id:
            row["done"] = value
            break
    for ev in st.session_state.events:
        if ev["id"] == row_id:
            ev["status"] = "completed" if value else "scheduled"
            break
    # recompute stats
    done_count = sum(1 for r in st.session_state.schedule_rows if r["done"])
    st.session_state.stats["completed"] = done_count


def quick_action(action: str):
    if action == "today":
        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": (
                    "Let’s plan **today’s schedule**.\n\n"
                    "You can paste your tasks or tell me your classes, meetings, and anything you want to get done."
                ),
            }
        )
    elif action == "add_event":
        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": (
                    "Sure, let’s **add an event**.\n\n"
                    "Tell me the event name, whether it’s fixed or flexible, and its approximate time and duration."
                ),
            }
        )
    elif action == "this_week":
        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": (
                    "Okay, let’s look at **this week**.\n\n"
                    "Tell me your big commitments (classes, recurring meetings, practice) and important tasks, "
                    "and I’ll help you block time across the week."
                ),
            }
        )
    elif action == "summary":
        completed = st.session_state.stats["completed"]
        total = st.session_state.stats["total"] or 1
        pct = int(100 * completed / total)
        msg = (
            f"In this session, you completed {completed}/{total} scheduled tasks "
            f"({pct}%).\n\n"
            "You can ask me for a 7‑day or 30‑day style summary, and I’ll describe trends "
            "based on what we’ve scheduled together."
        )
        st.session_state.messages.append({"role": "assistant", "content": msg})
    elif action == "connect_calendar":
        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": (
                    "Right now I only use data you share here.\n\n"
                    "In a full app, you could connect Google Calendar or similar, "
                    "but I’ll never claim to read them unless you explicitly connect them."
                ),
            }
        )


# ---------- QUICK ACTION BAR ----------
st.markdown("### Maite – AI Personal Scheduler")

qa_cols = st.columns([1, 1, 1, 1, 1])
if qa_cols[0].button("Today’s Schedule"):
    quick_action("today")
if qa_cols[1].button("Add Event"):
    quick_action("add_event")
if qa_cols[2].button("This Week"):
    quick_action("this_week")
if qa_cols[3].button("Summary"):
    quick_action("summary")
if qa_cols[4].button("Connect Calendar"):
    quick_action("connect_calendar")

st.markdown("---")

# ---------- MAIN LAYOUT (CHAT + EVENTS) ----------
col_chat, col_events = st.columns([2.3, 1.2])

# ----- Chat Area -----
with col_chat:
    st.subheader("Chat with Maite")

    # Display message history
    for m in st.session_state.messages:
        if m["role"] == "user":
            with st.chat_message("user"):
                st.markdown(m["content"])
        else:
            with st.chat_message("assistant"):
                st.markdown(m["content"])

    # Chat input
    user_input = st.chat_input("Tell Maite what you need help scheduling…")

    if user_input:
        # append user message
        st.session_state.messages.append({"role": "user", "content": user_input})

        with st.chat_message("user"):
            st.markdown(user_input)

        with st.chat_message("assistant"):
            with st.spinner("Maite is thinking about your schedule…"):
                reply = call_maite(SESSION_ID, user_input)
            st.markdown(reply)
            st.session_state.messages.append({"role": "assistant", "content": reply})

# ----- Events Panel -----
with col_events:
    st.subheader("Events Panel")

    if not st.session_state.events:
        st.caption("No events yet. Add tasks in chat, then turn them into schedule rows below.")
    else:
        for ev in st.session_state.events:
            st.markdown(f"**{ev['title']}** – {ev['time']}")
            if ev["status"] == "scheduled":
                st.markdown(
                    '<span class="maite-tag maite-tag-scheduled">scheduled</span>',
                    unsafe_allow_html=True,
                )
            elif ev["status"] == "completed":
                st.markdown(
                    '<span class="maite-tag maite-tag-completed">completed</span>',
                    unsafe_allow_html=True,
                )
            elif ev["status"] == "cancelled":
                st.markdown(
                    '<span class="maite-tag maite-tag-cancelled">cancelled</span>',
                    unsafe_allow_html=True,
                )
            st.markdown("---")

# ---------- SCHEDULE TABLE ----------
st.markdown("### Schedule Table")

# Demo controls to quickly add a row from UI (your backend can parse Maite's table later)
with st.expander("Add a task manually (for now)"):
    c1, c2 = st.columns(2)
    with c1:
        new_task = st.text_input("Task name", key="new_task_name")
        new_keywords = st.text_input(
            "Helpful keywords (focus, review, fixed, etc.)",
            key="new_task_kw",
        )
    with c2:
        new_time = st.text_input("Scheduled time (e.g., 4:00–4:45 PM)", key="new_task_time")
        kind = st.selectbox("Type", options=["flexible", "fixed"], index=0)
    if st.button("Add to schedule"):
        if new_task and new_time:
            add_schedule_row(new_task, new_time, new_keywords, kind=kind)
            st.success("Task added to schedule and events panel.")
        else:
            st.warning("Please provide at least a task name and time.")

if not st.session_state.schedule_rows:
    st.caption("No schedule yet. Ask Maite to create one based on your tasks.")
else:
    # Build a table-like layout with checkboxes that sync to events
    header_cols = st.columns([3, 2, 3, 1])
    header_cols[0].markdown("**Task**")
    header_cols[1].markdown("**Scheduled Time**")
    header_cols[2].markdown("**Helpful Keywords**")
    header_cols[3].markdown("**✓**")

    for row in st.session_state.schedule_rows:
        c_task, c_time, c_kw, c_check = st.columns([3, 2, 3, 1])
        c_task.write(row["task"])
        c_time.write(row["time"])
        c_kw.write(row["keywords"] or "-")
        checked = c_check.checkbox(
            "",
            value=row["done"],
            key=f"chk-{row['id']}",
            on_change=set_row_done,
            args=(row["id"], not row["done"]),
        )

# ---------- PROGRESS FOOTER ----------
comp = st.session_state.stats["completed"]
tot = st.session_state.stats["total"]
if tot > 0:
    pct = int(100 * comp / tot)
    st.markdown(
        f"**Progress:** {comp}/{tot} tasks completed ({pct}%). "
        "You can ask me for a short weekly or 30‑day style summary in chat."
    )
else:
    st.caption("Once you add tasks and complete them, I’ll show your progress here.")
