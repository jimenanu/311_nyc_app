import os
from openai import OpenAI


INTENT_RULES = {
    "Noise Complaint": {
        "keywords": ["noise", "loud", "music", "party", "neighbor", "barking"],
        "agency": "NYPD",
        "action": "Report through NYC 311 if the issue is ongoing."
    },
    "Heat / Hot Water": {
        "keywords": ["heat", "hot water", "no heat", "apartment", "landlord", "radiator"],
        "agency": "HPD",
        "action": "Submit a heat or hot water complaint through NYC 311."
    },
    "Illegal Parking": {
        "keywords": ["parking", "blocked driveway", "illegal parking", "car", "vehicle"],
        "agency": "NYPD",
        "action": "File an illegal parking complaint through NYC 311."
    },
    "Sanitation": {
        "keywords": ["trash", "garbage", "missed pickup", "dirty", "sanitation", "rats"],
        "agency": "DSNY",
        "action": "Report sanitation conditions through NYC 311."
    },
    "Street Condition": {
        "keywords": ["pothole", "street", "sidewalk", "road", "traffic light", "sign"],
        "agency": "DOT",
        "action": "Submit a street condition request through NYC 311."
    },
    "Emergency": {
        "keywords": ["fire", "crime", "danger", "injured", "weapon", "threat", "emergency"],
        "agency": "911",
        "action": "Call 911 immediately."
    }
}


def classify_intent(question):
    q = question.lower()
    scores = {}

    for intent, details in INTENT_RULES.items():
        matches = sum(1 for word in details["keywords"] if word in q)
        if matches > 0:
            scores[intent] = matches / len(details["keywords"])

    if not scores:
        return {
            "intent": "General 311 Request",
            "agency": "NYC 311",
            "confidence": 0.35,
            "escalation": "Review",
            "action": "Call 311 or visit NYC 311 online for the most appropriate service category."
        }

    best_intent = max(scores, key=scores.get)
    raw_confidence = scores[best_intent]

    confidence = min(0.95, max(0.55, raw_confidence + 0.45))

    details = INTENT_RULES[best_intent]

    if best_intent == "Emergency":
        escalation = "911"
    elif confidence < 0.65:
        escalation = "Review"
    else:
        escalation = "311 Online"

    return {
        "intent": best_intent,
        "agency": details["agency"],
        "confidence": round(confidence, 2),
        "escalation": escalation,
        "action": details["action"]
    }


def generate_311_response(question):
    result = classify_intent(question)

    if result["escalation"] == "911":
        response = (
            "This sounds like it may be urgent or unsafe. "
            "Please call 911 immediately instead of using 311."
        )
    else:
        api_key = os.getenv("OPENAI_API_KEY")

        if not api_key:
            response = (
                f"This appears to be a {result['intent']} issue. "
                f"The likely responsible agency is {result['agency']}. "
                f"Recommended next step: {result['action']}"
            )
        else:
            client = OpenAI(api_key=api_key)

            prompt = f"""
You are an NYC 311 GenAI call-deflection assistant.

The user's question is:
{question}

Classification:
- Intent: {result["intent"]}
- Responsible Agency: {result["agency"]}
- Confidence Score: {result["confidence"]}
- Escalation Recommendation: {result["escalation"]}
- Recommended Action: {result["action"]}

Write a concise, helpful response that:
1. Explains the likely issue
2. Recommends the next step
3. Mentions whether to use 311 online, call 311, or call 911
4. Does not overpromise resolution
"""

            completion = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
            )

            response = completion.choices[0].message.content

    return {
        "issue": result["intent"],
        "agency": result["agency"],
        "urgency": result["escalation"],
        "confidence": result["confidence"],
        "action": result["action"],
        "response": response
    }
