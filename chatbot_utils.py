import os
from openai import OpenAI


def classify_311_issue(question):
    q = question.lower()

    if any(x in q for x in ["fire", "crime", "danger", "emergency", "injured"]):
        return "Emergency", "911", "High"

    if any(x in q for x in ["noise", "loud", "music", "party"]):
        return "Noise Complaint", "NYPD", "Medium"

    if any(x in q for x in ["heat", "hot water", "landlord", "apartment"]):
        return "Heat / Hot Water", "HPD", "Medium"

    if any(x in q for x in ["trash", "garbage", "sanitation", "rats"]):
        return "Sanitation", "DSNY", "Medium"

    if any(x in q for x in ["parking", "blocked driveway", "illegal parking"]):
        return "Illegal Parking", "NYPD", "Medium"

    return "General 311 Request", "NYC 311", "Low"


def generate_311_response(question):

    issue, agency, urgency = classify_311_issue(question)

    if issue == "Emergency":
        return {
            "issue": issue,
            "agency": agency,
            "urgency": urgency,
            "response": (
                "This may be an emergency. "
                "Please call 911 immediately instead of using 311."
            )
        }

    api_key = os.getenv("OPENAI_API_KEY")

    # Fallback if no API key exists
    if not api_key:
        response = (
            f"This appears to be a {issue} issue. "
            f"The likely responsible agency is {agency}. "
            "You may report this through NYC 311."
        )

    else:

        client = OpenAI(api_key=api_key)

        prompt = f"""
You are an NYC 311 assistant.

User Question:
{question}

Issue Type:
{issue}

Agency:
{agency}

Urgency:
{urgency}

Provide:
- a short explanation
- likely next steps
- guidance for the resident
- keep response concise and professional
"""

        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.3,
        )

        response = completion.choices[0].message.content

    return {
        "issue": issue,
        "agency": agency,
        "urgency": urgency,
        "response": response
    }
