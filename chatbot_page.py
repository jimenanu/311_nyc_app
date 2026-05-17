import streamlit as st
import pandas as pd

from chatbot_engine import (
    DEFAULT_CONTEXT_PARQUET,
    DEFAULT_OPENAI_MODEL,
    genai_answer,
    load_chatbot_context,
)


def _get_openai_key_from_secrets() -> str:
    """
    Optional non-environment-variable key source.

    For local Streamlit, create:
    .streamlit/secrets.toml

    With:
    OPENAI_API_KEY = "sk-your-key-here"

    For Streamlit Community Cloud, add the same key under App settings > Secrets.
    """
    try:
        return st.secrets.get("OPENAI_API_KEY", "")
    except Exception:
        return ""


def render_chatbot_page():
    st.subheader("Ask the NYC 311 Chatbot")

    st.markdown(
        """
        Ask a common NYC 311 service question. The chatbot uses the project parquet context,
        optional live NYC Open Data examples, and OpenAI to generate a concise response.
        """
    )

    with st.expander("Chatbot settings", expanded=False):
        context_path = st.text_input(
    "Chatbot context parquet path",
    value="https://drive.google.com/uc?export=download&id=1d2MtRMFB8Oinw60BF1ia-gfCICfMGXhe",
    help="Google Drive direct link to chatbot_context.parquet.",
)

        model = st.text_input(
            "OpenAI model",
            value=DEFAULT_OPENAI_MODEL,
        )

        use_live_api = st.checkbox(
            "Use live NYC Open Data lookup",
            value=True,
            help="Turn this off if the API is slow during the demo.",
        )

        saved_key = _get_openai_key_from_secrets()
        if saved_key:
            st.success("OpenAI key loaded from Streamlit secrets.")
            api_key = saved_key
        else:
            api_key = st.text_input(
                "OpenAI API key",
                type="password",
                help="This is used only for the current app session. It is not saved by this app.",
            )

    try:
        chatbot_context_df = load_chatbot_context(context_path)
        st.caption(f"Loaded chatbot context rows: {len(chatbot_context_df):,}")
    except Exception as e:
        st.error("Could not load the chatbot context parquet.")
        st.exception(e)
        return

    if "chatbot_messages" not in st.session_state:
        st.session_state.chatbot_messages = []

    question = st.text_area(
        "Your question",
        placeholder="Example: My apartment has no heat. What should I do?",
        height=100,
    )

    ask_col, clear_col = st.columns([1, 1])

    with ask_col:
        ask_clicked = st.button("Ask Chatbot", use_container_width=True)

    with clear_col:
        if st.button("Clear Chat", use_container_width=True):
            st.session_state.chatbot_messages = []
            st.rerun()

    if ask_clicked:
        if not question.strip():
            st.warning("Please enter a NYC 311 question.")
            return

        if not api_key:
            st.warning("Please enter your OpenAI API key in Chatbot settings, or add it to Streamlit secrets.")
            return

        with st.spinner("Generating chatbot response..."):
            try:
                answer, meta = genai_answer(
                    question=question,
                    api_key=api_key,
                    chatbot_context_df=chatbot_context_df,
                    use_live_api=use_live_api,
                    return_metadata=True,
                    model=model,
                )

                st.session_state.chatbot_messages.append(
                    {
                        "question": question,
                        "answer": answer,
                        "metadata": meta,
                    }
                )

            except Exception as e:
                st.error("The chatbot could not generate a response.")
                st.exception(e)
                return

    if st.session_state.chatbot_messages:
        st.divider()
        st.subheader("Chatbot Response")

        for item in reversed(st.session_state.chatbot_messages):
            st.markdown("#### User Question")
            st.markdown(item["question"])

            st.markdown("#### Chatbot Answer")
            st.markdown(item["answer"])

            st.markdown("#### Metadata")
            meta = item.get("metadata", {})
            metadata_display = {
                "intent": meta.get("intent"),
                "confidence": meta.get("confidence"),
                "matched_terms": ", ".join(meta.get("matched_terms", [])) if isinstance(meta.get("matched_terms"), list) else meta.get("matched_terms"),
                "agency": meta.get("agency"),
                "recommended_action": meta.get("recommended_action"),
                "escalation": meta.get("escalation"),
            }
            st.dataframe(pd.DataFrame([metadata_display]), use_container_width=True)

            st.divider()
