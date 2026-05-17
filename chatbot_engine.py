import re
from pathlib import Path
from typing import Dict, List
import gdown
import pandas as pd
import requests
from openai import OpenAI


NYC_311_API = "https://data.cityofnewyork.us/resource/erm2-nwe9.json"
DEFAULT_CONTEXT_PARQUET = "chatbot_context.parquet"
DEFAULT_OPENAI_MODEL = "gpt-4.1-mini"


def load_chatbot_context(parquet_path: str = DEFAULT_CONTEXT_PARQUET) -> pd.DataFrame:
    """
    Load chatbot context from either:
    - local parquet file
    - downloadable URL, including Google Drive direct links
    """

    if str(parquet_path).startswith("http"):
    temp_path = "chatbot_context_temp.parquet"

    gdown.download(
        parquet_path,
        temp_path,
        quiet=False,
        fuzzy=True
    )

    df = pd.read_parquet(temp_path)
    source_name = "google_drive_context"

    else:
        path = Path(parquet_path)

        if not path.exists():
            raise FileNotFoundError(
                f"Parquet file not found: {path}. "
                "Place chatbot_context.parquet in the app folder or update the path in chatbot_page.py."
            )

        df = pd.read_parquet(path)
        source_name = path.name

    df.columns = (
        df.columns.astype(str)
        .str.strip()
        .str.lower()
        .str.replace(" ", "_", regex=False)
    )

    if "context_text" not in df.columns:
        def row_to_text(row):
            return " | ".join(
                f"{col}: {row[col]}" for col in row.index if pd.notna(row[col])
            )
        df["context_text"] = df.apply(row_to_text, axis=1)

    df["context_text"] = df["context_text"].astype(str)
    df["context_text_lower"] = df["context_text"].str.lower()

    if "context_type" not in df.columns:
        df["context_type"] = "general_project_context"

    if "source_file" not in df.columns:
        df["source_file"] = source_name

    if "topic_hint" not in df.columns:
        df["topic_hint"] = "general"

    return df

def nyc_api_get(params: Dict, timeout: int = 30) -> pd.DataFrame:
    """Small, safe NYC Open Data API request for demo use."""
    try:
        response = requests.get(NYC_311_API, params=params, timeout=timeout)
        response.raise_for_status()
        return pd.DataFrame(response.json())
    except Exception:
        return pd.DataFrame()


def get_live_recent_311_examples(limit: int = 10) -> pd.DataFrame:
    params = {
        "$select": "created_date, complaint_type, descriptor, agency, borough, status, resolution_description",
        "$order": "created_date DESC",
        "$limit": limit,
    }
    return nyc_api_get(params)


def search_live_311_examples(keyword: str, limit: int = 5) -> pd.DataFrame:
    df = get_live_recent_311_examples(limit=200)

    if df.empty:
        return pd.DataFrame()

    keyword_upper = keyword.upper()

    for col in ["complaint_type", "descriptor", "resolution_description"]:
        if col not in df.columns:
            df[col] = ""

    mask = (
        df["complaint_type"].astype(str).str.upper().str.contains(keyword_upper, na=False)
        | df["descriptor"].astype(str).str.upper().str.contains(keyword_upper, na=False)
        | df["resolution_description"].astype(str).str.upper().str.contains(keyword_upper, na=False)
    )

    return df[mask].head(limit)


def get_live_agency_for_complaint(complaint_keyword: str, limit: int = 10) -> pd.DataFrame:
    df = search_live_311_examples(complaint_keyword, limit=100)

    if df.empty or "agency" not in df.columns:
        return pd.DataFrame()

    return (
        df.groupby(["complaint_type", "agency"])
        .size()
        .reset_index(name="count")
        .sort_values("count", ascending=False)
        .head(limit)
    )


def get_live_top_complaint_types(limit: int = 10) -> pd.DataFrame:
    df = get_live_recent_311_examples(limit=500)

    if df.empty or "complaint_type" not in df.columns:
        return pd.DataFrame()

    top = df["complaint_type"].value_counts().head(limit).reset_index()
    top.columns = ["complaint_type", "count"]
    return top


def detect_basic_topic(question: str) -> str:
    q = question.lower()
    if any(x in q for x in ["heat", "hot water", "landlord", "apartment"]):
        return "Heat"
    if any(x in q for x in ["noise", "loud", "music", "neighbor"]):
        return "Noise"
    if any(x in q for x in ["parking", "blocked driveway", "illegal parking"]):
        return "Parking"
    if any(x in q for x in ["trash", "garbage", "sanitation", "missed collection"]):
        return "Sanitation"
    if any(x in q for x in ["tree", "street light", "pothole", "sidewalk"]):
        return "Street"
    return ""


def _keyword_terms(question: str) -> List[str]:
    stop_words = {
        "what", "when", "where", "which", "should", "could", "would", "about", "there",
        "this", "that", "with", "from", "have", "been", "does", "into", "your", "nyc",
        "311", "complaint", "complaints", "issue", "issues", "the", "and", "for", "can", "how",
    }
    raw_terms = [t.strip(".,?!:;()[]{}\"'").lower() for t in question.split()]
    return [t for t in raw_terms if len(t) >= 4 and t not in stop_words]


def retrieve_parquet_context(question: str, chatbot_context_df: pd.DataFrame, n: int = 10) -> str:
    """Retrieve local backup context from chatbot_context.parquet."""
    if chatbot_context_df is None or chatbot_context_df.empty:
        return ""

    df = chatbot_context_df.copy()
    q = question.lower()
    terms = _keyword_terms(question)
    score = pd.Series(0, index=df.index, dtype="int64")

    for term in terms:
        score += df["context_text_lower"].str.contains(term, na=False).astype(int)
        if "topic_hint" in df.columns:
            score += df["topic_hint"].astype(str).str.lower().str.contains(term, na=False).astype(int)
        if "context_type" in df.columns:
            score += df["context_type"].astype(str).str.lower().str.contains(term, na=False).astype(int)

    topic = detect_basic_topic(question).lower()
    if topic:
        score += df["context_text_lower"].str.contains(topic, na=False).astype(int) * 2
        if "topic_hint" in df.columns:
            score += df["topic_hint"].astype(str).str.lower().str.contains(topic, na=False).astype(int) * 2

    if any(x in q for x in ["top", "common", "volume", "highest", "most"]):
        score += df["context_type"].astype(str).str.contains("complaint_volume|kpi|agency|borough", case=False, na=False).astype(int)

    if any(x in q for x in ["borough", "brooklyn", "queens", "bronx", "manhattan", "staten"]):
        score += df["context_type"].astype(str).str.contains("borough", case=False, na=False).astype(int) * 2

    if any(x in q for x in ["agency", "department", "handled", "handles"]):
        score += df["context_type"].astype(str).str.contains("agency", case=False, na=False).astype(int) * 2

    if any(x in q for x in ["delay", "response", "long", "slow", "time"]):
        score += df["context_type"].astype(str).str.contains("delay|response|kpi", case=False, na=False).astype(int) * 2

    if any(x in q for x in ["repeat", "recurring"]):
        score += df["context_type"].astype(str).str.contains("repeat", case=False, na=False).astype(int) * 2

    matches = (
        df.loc[score > 0]
        .assign(_score=score[score > 0])
        .sort_values("_score", ascending=False)
        .head(n)
    )

    if matches.empty:
        fallback_types = ["kpi_summary", "complaint_volume", "agency_performance", "borough_performance", "delay_risk"]
        matches = df[df["context_type"].isin(fallback_types)].head(n)
        if matches.empty:
            matches = df.head(n)

    keep_cols = [c for c in ["source_file", "context_type", "topic_hint", "context_text"] if c in matches.columns]
    return "Local parquet backup context:\n" + matches[keep_cols].to_markdown(index=False)


def retrieve_project_context(question: str, chatbot_context_df: pd.DataFrame) -> str:
    return retrieve_parquet_context(question, chatbot_context_df, n=10)


def retrieve_live_context(question: str) -> str:
    q = question.lower()
    parts = []
    topic = detect_basic_topic(question)

    if any(x in q for x in ["top", "common", "highest volume", "most common"]):
        df = get_live_top_complaint_types(10)
        if not df.empty:
            parts.append("Live NYC Open Data top complaint types:\n" + df.to_markdown(index=False))

    if topic:
        examples = search_live_311_examples(topic, 5)
        if not examples.empty:
            parts.append(f"Recent NYC Open Data examples matching '{topic}':\n" + examples.to_markdown(index=False))

        agency = get_live_agency_for_complaint(topic, 10)
        if not agency.empty:
            parts.append(f"Common agencies for '{topic}' complaints:\n" + agency.to_markdown(index=False))

    return "\n\n".join(parts)


INTENT_RULES = {
    "noise_complaint": ["noise", "loud", "music", "party", "car alarm", "barking", "neighbor", "upstairs", "construction noise"],
    "heat_hot_water": ["heat", "hot water", "no heat", "radiator", "landlord", "apartment cold"],
    "housing_condition": ["mold", "leak", "ceiling", "stairs", "hallway", "building", "broken", "roach", "apartment"],
    "trash_sanitation": ["trash", "garbage", "recycling", "missed collection", "illegal dumping", "overflowing", "furniture", "sanitation"],
    "street_sidewalk": ["pothole", "sidewalk", "streetlight", "street light", "traffic signal", "traffic light", "street sign", "road"],
    "parking_vehicle": ["parking", "blocked driveway", "abandoned vehicle", "bus stop", "no plates", "vehicle", "car"],
    "rodents_pests": ["rat", "rats", "rodent", "pest", "roach", "mice", "mouse"],
    "parks_public_space": ["park", "playground", "tree", "branch", "dead tree", "graffiti", "bathroom"],
    "status_followup": ["status", "already filed", "complaint was closed", "closed", "reopen", "service request", "no action taken", "how long"],
    "analysis_question": ["most common", "highest", "leadership", "patterns", "borough", "agency", "delay", "longest", "focus", "analysis"],
}

EMERGENCY_TERMS = [
    "fire", "smoke", "gas smell", "smell gas", "carbon monoxide", "injured", "hurt", "medical emergency",
    "crime in progress", "breaking into", "assault", "shooting", "weapon", "immediate danger", "someone may be hurt",
]

DANGEROUS_311_TERMS = [
    "traffic light is out", "traffic signal is not working", "tree fell", "downed wire", "sinkhole", "dangerous", "hazard",
]

INTENT_TO_AGENCY = {
    "noise_complaint": "NYPD or DEP depending on the noise source",
    "heat_hot_water": "HPD",
    "housing_condition": "HPD",
    "trash_sanitation": "DSNY",
    "street_sidewalk": "DOT or DSNY depending on the issue",
    "parking_vehicle": "NYPD or DOT depending on the vehicle issue",
    "rodents_pests": "DOHMH",
    "parks_public_space": "NYC Parks",
    "status_followup": "NYC 311 / responsible agency listed on the service request",
    "analysis_question": "Analysis output, not a single agency",
}

INTENT_TO_ACTION = {
    "noise_complaint": "File a 311 noise complaint if the issue is ongoing and not an emergency.",
    "heat_hot_water": "File a 311 heat or hot water complaint and include building details.",
    "housing_condition": "File a 311 housing maintenance complaint with location and condition details.",
    "trash_sanitation": "File a 311 sanitation complaint and include the location and type of missed or improper collection.",
    "street_sidewalk": "File a 311 street or sidewalk condition complaint with the exact location.",
    "parking_vehicle": "File a 311 illegal parking or abandoned vehicle complaint if it is not an emergency.",
    "rodents_pests": "File a 311 rodent or pest complaint and include where the activity was seen.",
    "parks_public_space": "File a 311 parks or tree condition complaint with the park/location details.",
    "status_followup": "Use the service request number to check status through NYC 311 or the official 311 portal.",
    "analysis_question": "Use the project output tables to support leadership recommendations.",
}


def classify_intent(question: str) -> Dict:
    q = question.lower().strip()

    emergency_hits = [term for term in EMERGENCY_TERMS if term in q]
    if emergency_hits:
        return {
            "intent": "emergency",
            "confidence": 1.0,
            "matched_terms": emergency_hits,
            "agency": "911",
            "recommended_action": "Call 911 immediately if there is danger, a crime in progress, fire, medical emergency, or possible injury.",
            "escalation": "911",
        }

    scores = []
    for intent, keywords in INTENT_RULES.items():
        hits = [kw for kw in keywords if kw in q]
        if hits:
            confidence = min(0.95, 0.45 + (0.15 * len(hits)))
            scores.append((intent, confidence, hits))

    if not scores:
        return {
            "intent": "unclear_general",
            "confidence": 0.30,
            "matched_terms": [],
            "agency": "NYC 311",
            "recommended_action": "Ask a clarifying question or contact 311 if the issue needs official city support.",
            "escalation": "311",
        }

    scores.sort(key=lambda x: x[1], reverse=True)
    intent, confidence, hits = scores[0]

    escalation = "none"
    if any(term in q for term in DANGEROUS_311_TERMS):
        escalation = "311_urgent_or_911_if_immediate_danger"
    elif confidence < 0.50:
        escalation = "311"

    return {
        "intent": intent,
        "confidence": round(confidence, 2),
        "matched_terms": hits,
        "agency": INTENT_TO_AGENCY.get(intent, "NYC 311"),
        "recommended_action": INTENT_TO_ACTION.get(intent, "Contact NYC 311 for guidance."),
        "escalation": escalation,
    }


def get_common_issue_context(intent: str, chatbot_context_df: pd.DataFrame, top_n: int = 5) -> str:
    intent_terms = {
        "noise_complaint": ["noise", "loud", "music", "barking"],
        "heat_hot_water": ["heat", "hot water", "radiator"],
        "housing_condition": ["mold", "plumbing", "maintenance", "housing", "leak"],
        "trash_sanitation": ["trash", "garbage", "sanitation", "recycling", "dumping"],
        "street_sidewalk": ["pothole", "sidewalk", "street", "traffic", "signal"],
        "parking_vehicle": ["parking", "vehicle", "blocked driveway"],
        "rodents_pests": ["rodent", "rat", "pest", "roach"],
        "parks_public_space": ["park", "tree", "graffiti"],
        "status_followup": ["status", "closed", "service request", "reopen"],
        "analysis_question": ["kpi", "agency", "borough", "delay", "volume", "common"],
    }.get(intent, [])

    if not intent_terms or chatbot_context_df is None or chatbot_context_df.empty:
        return ""

    df = chatbot_context_df.copy()
    mask = pd.Series(False, index=df.index)
    for term in intent_terms:
        mask = mask | df["context_text_lower"].str.contains(term, na=False)
        if "topic_hint" in df.columns:
            mask = mask | df["topic_hint"].astype(str).str.lower().str.contains(term, na=False)

    matches = df.loc[mask].head(top_n)
    if matches.empty:
        return ""

    keep_cols = [c for c in ["source_file", "context_type", "topic_hint", "context_text"] if c in matches.columns]
    return "Common issue lookup from local parquet:\n" + matches[keep_cols].to_markdown(index=False)


def format_decision_summary(meta: Dict) -> str:
    matched = ", ".join(meta.get("matched_terms", [])) if meta.get("matched_terms") else "none"
    return f"""
Structured decision metadata:
- Intent: {meta.get('intent')}
- Confidence: {meta.get('confidence')}
- Matched terms: {matched}
- Likely agency: {meta.get('agency')}
- Recommended action: {meta.get('recommended_action')}
- Escalation route: {meta.get('escalation')}
""".strip()


SYSTEM_INSTRUCTIONS = """
You are a NYC 311 GenAI call-deflection assistant prototype project.

Your role:
- Interpret the user's issue in plain English.
- Use the structured decision metadata as the primary routing signal.
- Suggest the likely 311 complaint category when evidence supports it.
- Mention the likely responsible agency when evidence supports it.
- Use historical/project evidence to explain expected patterns.
- Give practical next steps.
- Be clear that this prototype does not submit official 311 requests or check live request status.
- For emergencies, safety threats, crimes in progress, fire, gas smell, or medical issues, tell the user to call 911.

Required response format:
1. Likely issue
2. Recommended next step
3. Agency or service area
4. Notes from project or NYC 311 data, if available
5. Escalation guidance if needed

Rules:
- Do not invent exact response times unless provided in the evidence.
- If confidence is low or the issue is unclear, say the chatbot cannot determine the issue confidently and recommend contacting 311.
- If evidence is limited, say so.
- Keep responses concise but helpful.
- Use a calm, public-service tone.
"""


def genai_answer(
    question: str,
    api_key: str,
    chatbot_context_df: pd.DataFrame,
    use_live_api: bool = False,
    return_metadata: bool = False,
    model: str = DEFAULT_OPENAI_MODEL,
):
    """
    Generate a NYC 311 chatbot response.

    The API key is passed directly from the Streamlit page.
    This avoids relying on an environment variable.
    """
    if not api_key:
        raise ValueError("OpenAI API key is required.")

    decision_meta = classify_intent(question)

    if decision_meta["intent"] == "emergency":
        answer = """Likely issue: Emergency or possible immediate danger.

Recommended next step: Call 911 immediately. This chatbot prototype does not handle emergencies or submit official reports.

Agency or service area: 911 emergency services.

Escalation guidance: If anyone may be hurt, there is fire, a crime in progress, or a possible gas leak, use 911 rather than 311."""
        return (answer, decision_meta) if return_metadata else answer

    project_context = retrieve_project_context(question, chatbot_context_df)
    common_issue_context = get_common_issue_context(decision_meta.get("intent", ""), chatbot_context_df)
    live_context = retrieve_live_context(question) if use_live_api else ""

    evidence = f"""
{format_decision_summary(decision_meta)}

PROJECT OUTPUT CONTEXT:
{project_context if project_context else "No project context matched."}

COMMON ISSUE LOOKUP:
{common_issue_context if common_issue_context else "No common issue lookup matched."}

LIVE NYC OPEN DATA CONTEXT:
{live_context if live_context else "No live NYC Open Data context retrieved."}
"""

    user_prompt = f"""
User question:
{question}

Evidence:
{evidence}

Please answer as a NYC 311 GenAI call-deflection assistant prototype.
"""

    client = OpenAI(api_key=api_key)

    response = client.responses.create(
        model=model,
        input=[
            {"role": "system", "content": SYSTEM_INSTRUCTIONS},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.2,
    )

    answer = response.output_text
    return (answer, decision_meta) if return_metadata else answer
