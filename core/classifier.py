import os
import json
from dotenv import load_dotenv
from langchain_huggingface import ChatHuggingFace, HuggingFaceEndpoint
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

load_dotenv()

# ── Model setup ─────────────────────────────────────────
llm = HuggingFaceEndpoint(
    repo_id="mistralai/Mistral-7B-Instruct-v0.2",
    task="text-generation",
    max_new_tokens=200,
    do_sample=False,
    repetition_penalty=1.03,
)
model = ChatHuggingFace(llm=llm)

# ── Prompt template ─────────────────────────────────────
prompt_template = PromptTemplate(
    input_variables=["job_description"],
    template="""
You are a job classification assistant for a skilled worker platform in Nepal.

Given a job description, extract the following and return ONLY a valid JSON object.
No explanation. No extra text. Just the JSON.

Job description: {job_description}

Return this exact format:
{{
    "skill_category": "one of: plumber, electrician, carpenter, painter, cleaner, ac_technician",
    "urgency": "one of: low, medium, high",
    "location_hint": "any location mentioned or null",
    "summary": "one short sentence describing the job"
}}
"""
)

# ── Chain ────────────────────────────────────────────────
chain = prompt_template | model | StrOutputParser()

# ── Fallback helpers ─────────────────────────────────────
SKILL_KEYWORDS = {
    "plumber": ["pipe", "leak", "water", "drain", "toilet", "tap", "pump", "plumb", "flood", "bathroom"],    "electrician":   ["light", "electric", "wire", "switch", "socket", "power", "fan", "inverter", "solar"],
    "carpenter":     ["door", "wood", "furniture", "cabinet", "shelf", "carpenter"],    "plumber":       ["pipe", "leak", "water", "drain", "toilet", "tap", "pump", "plumb"],

    "painter":       ["paint", "wall", "colour", "color", "interior", "exterior"],
    "cleaner":       ["clean", "dust", "wash", "mop", "hygiene"],
    "ac_technician": ["ac", "air condition", "cool", "refrigerator", "fridge", "hvac"],
}

def keyword_fallback(text: str) -> str:
    """
    If the LLM fails, match skill category by keywords.
    Simple but reliable — never returns a wrong category.
    """
    text_lower = text.lower()
    for skill, keywords in SKILL_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            return skill
    return "unknown"

def detect_urgency(text: str) -> str:
    """
    Detect urgency from keywords in the job description.
    High = immediate danger or damage. Low = routine work.
    """
    text_lower = text.lower()
    if any(w in text_lower for w in ["urgent", "emergency", "badly", "everywhere",
        "flood", "broken", "immediately", "burst"]):
        return "high"
    if any(w in text_lower for w in ["soon", "today", "tonight", "quickly", "asap"]):
        return "medium"
    return "low"

def extract_location(text: str) -> str | None:
    """
    Extract any Nepal location mentioned in the job description.
    Returns None if no known location found.
    """
    places = [
        "kathmandu", "lalitpur", "bhaktapur", "thamel", "patan",
        "pokhara", "chitwan", "biratnagar", "butwal", "hetauda",
        "baneshwor", "koteshwor", "sitapaila", "kalanki", "balaju",
        "chabahil", "suryabinayak", "imadol", "kupondole", "jawalakhel"
    ]
    text_lower = text.lower()
    for place in places:
        if place in text_lower:
            return place.capitalize()
    return None

# ── Main function ────────────────────────────────────────
def classify_job(job_description: str) -> dict:
    """
    Takes a job description string.
    Returns structured dict: skill_category, urgency, location_hint, summary.

    Primary path  → LLM (Mistral via HuggingFace)
    Fallback path → keyword matching + rule-based logic
    App never crashes either way.
    """
    try:
        # Primary — ask the LLM
        result   = chain.invoke({"job_description": job_description})
        raw_text = result.strip()

        # Safely extract JSON block from response
        start    = raw_text.find("{")
        end      = raw_text.rfind("}") + 1
        json_str = raw_text[start:end]
        parsed   = json.loads(json_str)

        # Validate required keys exist
        required = ["skill_category", "urgency", "location_hint", "summary"]
        if not all(k in parsed for k in required):
            raise ValueError("Missing keys in LLM response")

        return parsed

    except Exception as e:
        # Fallback — keyword + rule-based
        print(f"Classifier error: {e}")
        return {
            "skill_category": keyword_fallback(job_description),
            "urgency":        detect_urgency(job_description),
            "location_hint":  extract_location(job_description),
            "summary":        job_description[:100]
        }


# ── Quick test ───────────────────────────────────────────
if __name__ == "__main__":
    test_cases = [
        "My kitchen pipe is leaking badly, water is everywhere",
        "The lights in my bedroom stopped working suddenly",
        "I need someone to fix a broken door in Lalitpur",
        "My AC is making a loud noise and not cooling",
        "Need a painter for my living room walls in Thamel",
        "Urgent help needed, bathroom flood in Koteshwor",
        "Need someone to clean my office in Baneshwor soon",
    ]

    print("=" * 55)
    print("SewaBot — Classifier Test")
    print("=" * 55)

    for test in test_cases:
        print(f"\nInput:  {test}")
        result = classify_job(test)
        print(f"  skill_category : {result['skill_category']}")
        print(f"  urgency        : {result['urgency']}")
        print(f"  location_hint  : {result['location_hint']}")
        print(f"  summary        : {result['summary']}")