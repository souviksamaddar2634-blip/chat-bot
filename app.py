
import streamlit as st
import google.generativeai as genai
import os
from uuid import uuid4
from datetime import date
from dotenv import load_dotenv

# Load environment variables from the .env file
load_dotenv()

# --- Page Configuration ---
st.set_page_config(page_title="AI To-Do Assistant", page_icon="📝", layout="wide")
st.title("📝 AI To-Do Assistant")
st.caption("A sleek, organized place to manage tasks — with an AI helper on the side.")

# --- Inject a bit of CSS for nicer styling ---
st.markdown(
    """
    <style>
    .stat-card {
        padding: 1rem; border-radius: 12px; background: #f6f8fa; border: 1px solid #e3e7ee;
    }
    .todo-row { padding: 0.6rem 0.8rem; border-bottom: 1px dashed #e9ecef; }
    .todo-text { font-size: 1rem; }
    .todo-text.done { text-decoration: line-through; color: #6c757d; }
    .chip { display: inline-block; padding: 0.1rem 0.6rem; border-radius: 999px; font-size: 0.8rem; margin-left: 0.4rem; }
    .chip.low { background: #e6f4ea; color: #1e7e34; border: 1px solid #cdebd6; }
    .chip.medium { background: #fff4e5; color: #b45309; border: 1px solid #ffe8cc; }
    .chip.high { background: #fde8e8; color: #b91c1c; border: 1px solid #fbd5d5; }
    .chip.date { background: #eef2ff; color: #4338ca; border: 1px solid #e0e7ff; }
    .toolbar { padding: 0.5rem 0; }
    .sr-only { position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px; overflow: hidden; clip: rect(0,0,0,0); border: 0; }
    </style>
    """,
    unsafe_allow_html=True,
)

# --- Secure API Key Setup ---
api_key = os.getenv("GEMINI_API_KEY")
ai_enabled = bool(api_key)

if not ai_enabled:
    st.info("Gemini API key not found. The AI assistant is disabled. To enable it, set GEMINI_API_KEY in your .env file.")
else:
    genai.configure(api_key=api_key)

# --- Initialize Chat Session (only if AI enabled) ---
if ai_enabled and "chat_session" not in st.session_state:
    model = genai.GenerativeModel(
        model_name="gemini-2.5-flash",
        system_instruction=(
            "You are a highly organized, concise To-Do list assistant. "
            "Keep a running list of their tasks in your memory. "
            "When they add, remove, or complete a task, confirm the action and always output the updated to-do list."
        ),
    )
    st.session_state.chat_session = model.start_chat(history=[])

# --- Initialize To-Do state ---
if "todos" not in st.session_state:
    st.session_state.todos = []  # each: {id, text, done, priority, due_date}

# Helper functions

def add_todo(text: str, priority: str = "Medium", due: date | None = None):
    text = (text or "").strip()
    if not text:
        st.warning("Please enter a task description.")
        return
    st.session_state.todos.append(
        {
            "id": str(uuid4()),
            "text": text,
            "done": False,
            "priority": priority,
            "due_date": due.isoformat() if due else None,
        }
    )
    st.toast("Task added ✅")


def toggle_done(todo_id: str, done: bool):
    for t in st.session_state.todos:
        if t["id"] == todo_id:
            t["done"] = done
            break


def delete_todo(todo_id: str):
    st.session_state.todos = [t for t in st.session_state.todos if t["id"] != todo_id]
    st.toast("Task removed 🗑️")


def filtered_todos(filter_name: str):
    todos = st.session_state.todos
    if filter_name == "Active":
        return [t for t in todos if not t["done"]]
    if filter_name == "Completed":
        return [t for t in todos if t["done"]]
    return todos


def todo_stats():
    total = len(st.session_state.todos)
    completed = sum(1 for t in st.session_state.todos if t["done"]) 
    active = total - completed
    return total, active, completed

# --- Layout ---
left, right = st.columns([0.62, 0.38])

with left:
    st.subheader("Your To-Dos")

    with st.container(border=True):
        with st.form("add_todo_form", clear_on_submit=True):
            new_todo = st.text_input("Add a task", placeholder="e.g. Review pull requests", label_visibility="collapsed")
            c1, c2, c3 = st.columns([0.4, 0.3, 0.3])
            with c1:
                priority = st.selectbox("Priority", ["Low", "Medium", "High"], index=1)
            with c2:
                due = st.date_input("Due date", value=None, format="YYYY-MM-DD")
            with c3:
                submitted = st.form_submit_button("Add Task", use_container_width=True, type="primary")
            if submitted:
                add_todo(new_todo, priority, due)

    with st.expander("Quick add multiple tasks (one per line)"):
        multi_text = st.text_area("", placeholder="Task one\nTask two\nTask three ...", height=100, label_visibility="collapsed")
        if st.button("Add All", use_container_width=True):
            lines = [ln.strip() for ln in (multi_text or "").splitlines() if ln.strip()]
            for ln in lines:
                add_todo(ln)

    # Toolbar: search + bulk actions
    with st.container():
        st.markdown('<div class="toolbar"></div>', unsafe_allow_html=True)
        t1, t2, t3 = st.columns([0.6, 0.2, 0.2])
        with t1:
            q = st.text_input("Search", placeholder="Filter tasks by text ...", label_visibility="collapsed", key="search")
        with t2:
            if st.button("Clear completed"):
                before = len(st.session_state.todos)
                st.session_state.todos = [t for t in st.session_state.todos if not t["done"]]
                removed = before - len(st.session_state.todos)
                st.toast(f"Cleared {removed} completed task(s)")
        with t3:
            if st.button("Clear all", type="secondary"):
                st.session_state.todos = []
                st.toast("All tasks cleared 🧹")

    # Removed white stat cards as requested

    # Tabs for All / Active / Completed
    tabs = st.tabs(["All", "Active", "Completed"])
    filters = ["All", "Active", "Completed"]
    for tab, fname in zip(tabs, filters):
        with tab:
            visible = filtered_todos(fname)
            if q:
                visible = [t for t in visible if q.lower() in t["text"].lower()]

            if not visible:
                st.info("No tasks here yet.")
            else:
                for t in visible:
                    # Render row
                    rid = t["id"]
                    cbox, main, actions = st.columns([0.1, 0.7, 0.2], vertical_alignment="center")
                    with cbox:
                        val = st.checkbox(" ", value=t["done"], key=f"{fname}_cb_{rid}")
                        if val != t["done"]:
                            toggle_done(rid, val)
                    with main:
                        classes = "todo-text done" if t["done"] else "todo-text"
                        line = f"<span class='{classes}'>{st.session_state.get('search_highlight', '')}</span>"
                        st.markdown(f"<div class='todo-row'><span class='{classes}'>{t['text']}</span>" \
                                    + (f"<span class='chip {t['priority'].lower()}'>" + t['priority'] + "</span>" if t.get('priority') else "") \
                                    + (f"<span class='chip date'>Due: {t['due_date']}</span>" if t.get('due_date') else "") \
                                    + "</div>", unsafe_allow_html=True)
                    with actions:
                        del_key = f"{fname}_del_{rid}"
                        if st.button("Delete", key=del_key):
                            delete_todo(rid)
                            st.experimental_rerun()

with right:
    st.subheader("AI Assistant")

    if ai_enabled:
        # Reset chat control
        reset_col, _a, _b = st.columns([0.4, 0.3, 0.3])
        with reset_col:
            if st.button("Reset chat", type="secondary", help="Clear conversation and start fresh"):
                try:
                    model = genai.GenerativeModel(
                        model_name="gemini-2.5-flash",
                        system_instruction=(
                            "You are a highly organized, concise To-Do list assistant. "
                            "Keep a running list of their tasks in your memory. "
                            "When they add, remove, or complete a task, confirm the action and always output the updated to-do list."
                        ),
                    )
                    st.session_state.chat_session = model.start_chat(history=[])
                    st.success("AI chat reset.")
                except Exception as e:
                    st.error(f"Failed to reset: {e}")

        # Quick actions
        cqa1, cqa2, cqa3 = st.columns(3)
        if cqa1.button("Suggest next 3"):
            tasks_text = "\n".join([f"- {'[x]' if t['done'] else '[ ]'} {t['text']} (P:{t['priority']}{', Due ' + t['due_date'] if t['due_date'] else ''})" for t in st.session_state.todos]) or "(none)"
            prompt = (
                "Here are my current tasks (with status, priority, due dates):\n" + tasks_text +
                "\n\nSuggest the next 3 tasks I should tackle today with a short reasoning."
            )
            with st.spinner("Thinking..."):
                try:
                    resp = st.session_state.chat_session.send_message(prompt)
                    st.markdown(resp.text)
                except Exception as e:
                    st.error(f"AI error: {e}")

        if cqa2.button("Prioritize all"):
            tasks_text = "\n".join([f"- {'[x]' if t['done'] else '[ ]'} {t['text']} (P:{t['priority']}{', Due ' + t['due_date'] if t['due_date'] else ''})" for t in st.session_state.todos]) or "(none)"
            prompt = (
                "Reorder and label my tasks by priority (High/Medium/Low) based on urgency and due dates. Tasks:\n" + tasks_text
            )
            with st.spinner("Prioritizing..."):
                try:
                    resp = st.session_state.chat_session.send_message(prompt)
                    st.markdown(resp.text)
                except Exception as e:
                    st.error(f"AI error: {e}")

        if cqa3.button("Summarize"):
            tasks_text = "\n".join([f"- {'[x]' if t['done'] else '[ ]'} {t['text']} (P:{t['priority']}{', Due ' + t['due_date'] if t['due_date'] else ''})" for t in st.session_state.todos]) or "(none)"
            prompt = (
                "Give me a short summary of my to-do list: what's done, what's pending, and any risks from due dates. Tasks:\n" + tasks_text
            )
            with st.spinner("Summarizing..."):
                try:
                    resp = st.session_state.chat_session.send_message(prompt)
                    st.markdown(resp.text)
                except Exception as e:
                    st.error(f"AI error: {e}")

        # Show chat history
        if hasattr(st.session_state, "chat_session"):
            for message in st.session_state.chat_session.history:
                role = "assistant" if getattr(message, "role", "") == "model" else "user"
                with st.chat_message(role):
                    # message.parts may differ by SDK object; handle text fallback
                    try:
                        st.markdown(message.parts[0].text)
                    except Exception:
                        st.write(str(message))

        # Chat input
        if prompt := st.chat_input("Ask the assistant or type a command (e.g., 'Add \"Review PRs\"')..."):
            with st.chat_message("user"):
                st.markdown(prompt)
            with st.chat_message("assistant"):
                with st.spinner("Processing..."):
                    try:
                        response = st.session_state.chat_session.send_message(prompt)
                        st.markdown(response.text)
                    except Exception as e:
                        st.error(f"An error occurred: {e}")
    else:
        st.info("AI panel is disabled. Add GEMINI_API_KEY to your .env to enable AI features.")