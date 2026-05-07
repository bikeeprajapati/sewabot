import os
import json
from dotenv import load_dotenv
from langchain_huggingface import HuggingFaceEndpoint
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

load_dotenv()

# ── Model setup ─────────────────────────────────────────
llm = HuggingFaceEndpoint(
    repo_id="mistralai/Mistral-7B-Instruct-v0.3",
    huggingfacehub_api_token=os.getenv("HUGGINGFACEHUB_API_TOKEN"),
    temperature=0.1,        # low = more consistent, structured output
    max_new_tokens=200,
)

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
chain = prompt_template | llm | StrOutputParser()

# ── Main function ────────────────────────────────────────
def classify_job(job_description: str) -> dict:
    """
    Takes a job description string.
    Returns a structured dict with skill_category, urgency, location_hint, summary.
    """
    try:
        result = chain.invoke({"job_description": job_description})
        raw_text = result["text"].strip()

        # Extract JSON safely — model sometimes adds extra text
        start = raw_text.find("{")
        end   = raw_text.rfind("}") + 1
        json_str = raw_text[start:end]

        parsed = json.loads(json_str)
        return parsed

    except Exception as e:
        # Fallback — so the app never crashes even if model fails
        print(f"Classifier error: {e}")
        return {
            "skill_category": "unknown",
            "urgency": "medium",
            "location_hint": None,
            "summary": job_description
        }


# ── Quick test ───────────────────────────────────────────
if __name__ == "__main__":
    test_cases = [
        "My kitchen pipe is leaking badly, water is everywhere",
        "The lights in my bedroom stopped working suddenly",
        "I need someone to fix a broken door in Lalitpur",
        "My AC is making a loud noise and not cooling",
        "Need a painter for my living room walls in Thamel",
    ]

    for test in test_cases:
        print(f"\nInput:  {test}")
        result = classify_job(test)
        print(f"Output: {json.dumps(result, indent=2)}")