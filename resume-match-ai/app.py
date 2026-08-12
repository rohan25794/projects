"""
Streamlit UI for the Resume-to-Job Match AI project.

Run with:
    streamlit run app.py
"""

import streamlit as st
import pdfplumber

from matcher import analyze

st.set_page_config(page_title="Resume-to-Job Match AI", page_icon="🧭", layout="wide")

st.title("🧭 Resume-to-Job Match AI")
st.caption(
    "Paste your resume and a job description to get a match score, "
    "an explanation of the score, and a skill-gap roadmap."
)


def extract_text_from_pdf(uploaded_file) -> str:
    text_chunks = []
    with pdfplumber.open(uploaded_file) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_chunks.append(page_text)
    return "\n".join(text_chunks)


col1, col2 = st.columns(2)

with col1:
    st.subheader("Resume")
    resume_file = st.file_uploader("Upload resume (PDF)", type=["pdf"])
    resume_text_input = st.text_area(
        "...or paste resume text here", height=250, key="resume_text"
    )

with col2:
    st.subheader("Job Description")
    job_text_input = st.text_area(
        "Paste the job description here", height=300, key="job_text"
    )

run_button = st.button("Analyze Match", type="primary")

if run_button:
    # Resolve resume text: uploaded PDF takes priority over pasted text.
    if resume_file is not None:
        resume_text = extract_text_from_pdf(resume_file)
    else:
        resume_text = resume_text_input

    job_text = job_text_input

    if not resume_text.strip() or not job_text.strip():
        st.warning("Please provide both a resume and a job description.")
    else:
        with st.spinner("Analyzing..."):
            result = analyze(resume_text, job_text)

        st.divider()

        score = result["score"]
        st.subheader(f"Match Score: {score}%")
        st.progress(int(score))

        st.markdown(f"**Explanation:** {result['explanation']}")

        col_a, col_b, col_c = st.columns(3)
        with col_a:
            st.markdown("### ✅ Matched Skills")
            if result["matched"]:
                for skill in result["matched"]:
                    st.write(f"- {skill}")
            else:
                st.write("None found.")

        with col_b:
            st.markdown("### ❌ Missing Skills")
            if result["missing"]:
                for skill in result["missing"]:
                    st.write(f"- {skill}")
            else:
                st.write("None — great coverage!")

        with col_c:
            st.markdown("### ➕ Extra Skills")
            st.caption("Skills on your resume not mentioned in the job post.")
            if result["extra"]:
                for skill in result["extra"]:
                    st.write(f"- {skill}")
            else:
                st.write("None.")

        if result["roadmap"]:
            st.divider()
            st.markdown("### 📍 Suggested Roadmap")
            for step in result["roadmap"]:
                st.write(f"- {step}")
