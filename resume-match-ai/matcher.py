"""
Core engine for the Resume-to-Job Match AI project.

Pipeline:
1. Embed resume text and job description text using a sentence-transformer.
2. Compute cosine similarity -> base match score.
3. Extract skills from both texts using a curated skill list.
4. Compare skill sets -> overlapping skills + missing skills.
5. Generate a human-readable explanation of the score.
6. Generate a simple "next steps" roadmap based on missing skills.
"""

import re
from functools import lru_cache

import numpy as np
from sentence_transformers import SentenceTransformer

from skills_db import SKILLS_DB


@lru_cache(maxsize=1)
def get_model():
    """
    Load the embedding model once and cache it.
    all-MiniLM-L6-v2 is small, fast, and runs fine on CPU.
    """
    return SentenceTransformer("all-MiniLM-L6-v2")


def embed_text(text: str) -> np.ndarray:
    model = get_model()
    return model.encode(text, convert_to_numpy=True)


def cosine_similarity(vec_a: np.ndarray, vec_b: np.ndarray) -> float:
    a_norm = vec_a / np.linalg.norm(vec_a)
    b_norm = vec_b / np.linalg.norm(vec_b)
    return float(np.dot(a_norm, b_norm))


def compute_match_score(resume_text: str, job_text: str) -> float:
    """
    Returns a 0-100 match score based on embedding similarity.
    Cosine similarity for sentence embeddings usually lands between
    ~0.2 (unrelated) and ~0.9 (near duplicate), so we rescale it
    into a more intuitive 0-100 range for the UI.
    """
    resume_vec = embed_text(resume_text)
    job_vec = embed_text(job_text)
    raw_sim = cosine_similarity(resume_vec, job_vec)

    # Rescale: treat 0.2 as 0% and 0.9 as 100%, clip outside that range.
    rescaled = (raw_sim - 0.2) / (0.9 - 0.2)
    score = max(0.0, min(1.0, rescaled)) * 100
    return round(score, 1)


def extract_skills(text: str) -> set:
    """
    Rule-based skill extraction: lowercase the text and check for each
    skill in SKILLS_DB as a whole-word / whole-phrase match.
    Simple, but transparent and explainable — no black box here.
    """
    text_lower = text.lower()
    found = set()
    for skill in SKILLS_DB:
        pattern = r"\b" + re.escape(skill) + r"\b"
        if re.search(pattern, text_lower):
            found.add(skill)
    return found


def compare_skills(resume_text: str, job_text: str):
    resume_skills = extract_skills(resume_text)
    job_skills = extract_skills(job_text)

    matched = sorted(resume_skills & job_skills)
    missing = sorted(job_skills - resume_skills)
    extra = sorted(resume_skills - job_skills)

    return {
        "matched": matched,
        "missing": missing,
        "extra": extra,
        "resume_skills": sorted(resume_skills),
        "job_skills": sorted(job_skills),
    }


def generate_explanation(score: float, skill_comparison: dict) -> str:
    matched = skill_comparison["matched"]
    missing = skill_comparison["missing"]

    if score >= 75:
        tone = "Strong match."
    elif score >= 50:
        tone = "Moderate match."
    else:
        tone = "Weak match."

    parts = [tone]

    if matched:
        parts.append(
            f"Your resume overlaps with the job on: {', '.join(matched[:6])}"
            + (", and more." if len(matched) > 6 else ".")
        )
    else:
        parts.append("No direct skill keyword overlap was found.")

    if missing:
        parts.append(
            f"The job description mentions skills not found in your resume: "
            f"{', '.join(missing[:6])}"
            + (", and more." if len(missing) > 6 else ".")
        )
    else:
        parts.append("No missing required skills detected.")

    return " ".join(parts)


def generate_roadmap(missing_skills: list) -> list:
    """
    Turns missing skills into a simple, actionable learning roadmap.
    This is intentionally simple (rule-based) — you can later swap this
    for an LLM call that generates richer, personalized suggestions.
    """
    roadmap = []
    for skill in missing_skills:
        roadmap.append(
            f"Learn the basics of '{skill}' and add a small project or "
            f"bullet point demonstrating it on your resume."
        )
    return roadmap


def analyze(resume_text: str, job_text: str) -> dict:
    """
    Runs the full pipeline and returns a single result dict for the UI.
    """
    score = compute_match_score(resume_text, job_text)
    skill_comparison = compare_skills(resume_text, job_text)
    explanation = generate_explanation(score, skill_comparison)
    roadmap = generate_roadmap(skill_comparison["missing"])

    return {
        "score": score,
        "explanation": explanation,
        "roadmap": roadmap,
        **skill_comparison,
    }
