import logging
from pathlib import Path

import streamlit as st

# ---------------------------------------------------------
# PAGE CONFIGURATION (Must be the very first Streamlit command)
# ---------------------------------------------------------
st.set_page_config(
    page_title="PakKnowledge AI",
    page_icon="🇵🇰",
    layout="centered",
    initial_sidebar_state="expanded",
)

# Render UI layout immediately so page renders on cold starts without delay
st.markdown(
    """
    <style>
    /* Sidebar spacing adjustments */
    section[data-testid="stSidebar"] div[data-testid="stSidebarContent"] {
        padding-top: 1.25rem;
        padding-bottom: 1rem;
    }

    section[data-testid="stSidebar"] .block-container {
        padding-top: 0.75rem;
        padding-bottom: 1rem;
        gap: 0.85rem;
    }

    section[data-testid="stSidebar"] [data-testid="stVerticalBlock"] {
        gap: 0.75rem;
    }

    section[data-testid="stSidebar"] hr {
        margin: 0.75rem 0;
    }

    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3 {
        margin-bottom: 0.3rem;
        padding-bottom: 0;
    }

    section[data-testid="stSidebar"] p {
        margin-bottom: 0.25rem;
        line-height: 1.45;
    }

    .pk-brand {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        padding: 0.25rem 0 0.5rem 0;
    }

    .pk-brand-mark {
        width: 42px;
        height: 42px;
        min-width: 42px;
        display: flex;
        align-items: center;
        justify-content: center;
        border-radius: 12px;
        background: #1B3EBF;
        color: #FFFFFF;
        font-size: 1.05rem;
        font-weight: 800;
        letter-spacing: -1px;
    }

    .pk-brand-name {
        color: var(--text-color);
        font-size: 1.08rem;
        font-weight: 750;
        line-height: 1.2;
    }

    .pk-brand-tagline {
        color: var(--secondary-text-color);
        font-size: 0.76rem;
        margin-top: 0.2rem;
    }

    .pk-section-label {
        color: var(--text-color);
        font-size: 0.94rem;
        font-weight: 700;
        margin: 0.2rem 0 0.25rem 0;
    }

    .pk-about {
        color: var(--secondary-text-color);
        font-size: 0.83rem;
        line-height: 1.45;
        margin: 0;
    }

    .pk-status {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 0.5rem;
        padding: 0.55rem 0.65rem;
        border-radius: 9px;
        background: var(--secondary-background-color);
        font-size: 0.82rem;
    }

    .pk-status-label {
        color: var(--text-color);
        font-weight: 600;
    }

    .pk-status-value {
        color: #0A9B70;
        font-weight: 700;
        white-space: nowrap;
    }

    .pk-chunk-count {
        color: var(--secondary-text-color);
        font-size: 0.77rem;
        margin: 0.35rem 0 0 0.1rem;
    }

    .pk-welcome {
        padding: 0.2rem 0;
    }

    .pk-welcome-title {
        font-size: 1.1rem;
        font-weight: 700;
        margin-bottom: 0.4rem;
    }

    .pk-welcome-copy {
        color: var(--secondary-text-color);
        font-size: 0.92rem;
        line-height: 1.55;
    }

    .pk-source-meta {
        color: var(--secondary-text-color);
        font-size: 0.82rem;
    }

    div[data-testid="stChatMessage"] {
        padding-top: 0.65rem;
        padding-bottom: 0.65rem;
    }

    div[data-testid="stExpander"] {
        border-radius: 10px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Lazy import core Graph logic after initial page layout setup
from graph import ask_question

PROJECT_ROOT = Path(__file__).resolve().parent
CHROMA_DIR = PROJECT_ROOT / "data" / "chroma_db"
COLLECTION_NAME = "pakknowledge_documents"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("pakknowledge")


# ---------------------------------------------------------
# SESSION STATE
# ---------------------------------------------------------

if "messages" not in st.session_state:
    st.session_state.messages = []


# ---------------------------------------------------------
# KNOWLEDGE BASE STATUS (CACHED RESOURCE FOR SPEED)
# ---------------------------------------------------------

@st.cache_resource(show_spinner=False)
def get_chroma_client(chroma_path: str):
    """Lazy-load and cache ChromaDB PersistentClient across sessions."""
    import chromadb
    return chromadb.PersistentClient(path=chroma_path)


@st.cache_data(ttl=60, show_spinner=False)
def get_knowledge_base_status() -> tuple[bool, int, str | None]:
    """Return ChromaDB connection status, indexed chunk count, and error."""
    try:
        if not CHROMA_DIR.exists():
            return False, 0, "The ChromaDB directory does not exist."

        client = get_chroma_client(str(CHROMA_DIR))
        collection = client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
        return True, collection.count(), None
    except Exception as exc:
        logger.exception("Could not read ChromaDB status")
        return False, 0, str(exc)


# ---------------------------------------------------------
# SOURCE DISPLAY HELPERS
# ---------------------------------------------------------

def render_sources(sources: list[dict]) -> None:
    """Render source references without exposing local machine paths."""
    if not sources:
        return

    with st.expander(f"View Sources ({len(sources)})", expanded=False):
        for index, source in enumerate(sources):
            source_id = source.get("id", f"Source {index + 1}")
            title = source.get("title") or "Untitled document"
            page = source.get("page")

            st.markdown(f"**[{source_id}] {title}**")

            if page is not None:
                st.caption(f"Page {page}")
            else:
                st.caption("Page information unavailable")

            if index < len(sources) - 1:
                st.divider()


def render_assistant_message(message: dict) -> None:
    st.markdown(message.get("content", ""))

    render_sources(message.get("sources", []))

    reason = message.get("verification_reason")
    if reason:
        with st.expander("Evidence verification details", expanded=False):
            st.caption(reason)

    diagnostic = message.get("diagnostic")
    if diagnostic:
        with st.expander("Technical diagnostic", expanded=False):
            st.code(diagnostic)


# ---------------------------------------------------------
# SIDEBAR
# ---------------------------------------------------------

with st.sidebar:
    st.markdown(
        """
        <div class="pk-brand">
            <div class="pk-brand-mark">PK</div>
            <div>
                <div class="pk-brand-name">PakKnowledge AI</div>
                <div class="pk-brand-tagline">Your Trusted Guide to Pakistan</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.divider()

    st.markdown('<div class="pk-section-label">About</div>', unsafe_allow_html=True)
    st.markdown(
        """
        <p class="pk-about">
            A Pakistan-focused knowledge assistant that provides
            evidence-based answers from trusted, indexed sources.
        </p>
        """,
        unsafe_allow_html=True,
    )

    st.divider()

    st.markdown(
        '<div class="pk-section-label">Knowledge Base</div>',
        unsafe_allow_html=True,
    )

    is_connected, chunk_count, knowledge_error = get_knowledge_base_status()

    if is_connected:
        st.markdown(
            """
            <div class="pk-status">
                <span class="pk-status-label">Database status</span>
                <span class="pk-status-value">● Connected</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<p class="pk-chunk-count">📄 {chunk_count:,} indexed chunks</p>',
            unsafe_allow_html=True,
        )
    else:
        st.error("Knowledge base unavailable")
        if knowledge_error:
            with st.expander("Connection details"):
                st.caption(knowledge_error)

    st.divider()

    if st.button(
        "＋  New Chat",
        use_container_width=True,
        type="primary",
    ):
        st.session_state.messages = []
        st.rerun()

    st.caption("Pakistan-focused Retrieval-Augmented Generation (RAG).")


# ---------------------------------------------------------
# WELCOME STATE
# ---------------------------------------------------------

if not st.session_state.messages:
    with st.chat_message("assistant", avatar="🇵🇰"):
        st.markdown(
            """
            <div class="pk-welcome">
                <div class="pk-welcome-title">
                    Welcome to PakKnowledge AI!
                </div>
                <div class="pk-welcome-copy">
                    Ask questions about Pakistan and receive answers
                    grounded in the indexed knowledge sources.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("**Explore topics such as:**")
        st.markdown(
            "- History, geography, and culture\n"
            "- Government, laws, and public services\n"
            "- Economy and education\n"
            "- Tourism and heritage"
        )


# ---------------------------------------------------------
# CONVERSATION HISTORY
# ---------------------------------------------------------

for message in st.session_state.messages:
    role = message["role"]
    avatar = "🧑" if role == "user" else "🇵🇰"

    with st.chat_message(role, avatar=avatar):
        if role == "assistant":
            render_assistant_message(message)
        else:
            st.markdown(message["content"])


# ---------------------------------------------------------
# CHAT INPUT AND RESPONSE GENERATION
# ---------------------------------------------------------

user_question = st.chat_input("Ask a question about Pakistan...")

if user_question:
    st.session_state.messages.append(
        {
            "role": "user",
            "content": user_question,
        }
    )

    with st.chat_message("user", avatar="🧑"):
        st.markdown(user_question)

    with st.chat_message("assistant", avatar="🇵🇰"):
        with st.spinner("Searching knowledge sources and verifying evidence..."):
            try:
                result = ask_question(user_question)

                answer = result.get(
                    "answer",
                    "I couldn't generate a response. Please try again.",
                )
                sources = result.get("sources") or []
                verification_reason = result.get("verification_reason")
                diagnostic = result.get("error")

                if diagnostic:
                    logger.error("Graph returned an error: %s", diagnostic)

                assistant_message = {
                    "role": "assistant",
                    "content": answer,
                    "sources": sources,
                    "verification_reason": verification_reason,
                    "diagnostic": diagnostic,
                }

                render_assistant_message(assistant_message)
                st.session_state.messages.append(assistant_message)

            except Exception as exc:
                logger.exception("Question processing failed")

                error_message = (
                    "An unexpected error occurred while processing "
                    "your question. Please try again. If the problem "
                    "continues, check the application terminal."
                )

                assistant_message = {
                    "role": "assistant",
                    "content": error_message,
                    "sources": [],
                    "verification_reason": None,
                    "diagnostic": str(exc),
                }

                st.error(error_message)
                st.session_state.messages.append(assistant_message)
