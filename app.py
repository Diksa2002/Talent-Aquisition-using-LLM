import streamlit as st
import os
import tempfile
from database import TalentDB
import parser
import matcher
import interview
import llm_client

# Page configuration
st.set_page_config(
    page_title="Talent AI - LLM Talent Acquisition",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for modern design and aesthetics
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700&display=swap');

/* Typography & Base styles */
html, body, [class*="css"] {
    font-family: 'Plus Jakarta Sans', sans-serif;
    font-size: 14px !important;
}

/* Custom card style */
.role-card {
    background: rgba(30, 41, 59, 0.45);
    backdrop-filter: blur(8px);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 12px;
    padding: 20px;
    margin-bottom: 15px;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.role-card:hover {
    transform: translateY(-3px);
    border-color: #6366f1;
    box-shadow: 0 10px 25px rgba(99, 102, 241, 0.15);
}

/* Gradient headings */
.main-title {
    background: linear-gradient(135deg, #6366f1, #a855f7);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    font-weight: 800;
    font-size: 2.0rem;
    margin-bottom: 0.5rem;
}

.subtitle {
    color: #94a3b8;
    font-size: 0.95rem;
    margin-bottom: 2rem;
}

/* Score Pill */
.score-badge {
    background: linear-gradient(135deg, #3b82f6, #1d4ed8);
    color: white;
    padding: 4px 10px;
    border-radius: 9999px;
    font-size: 0.85rem;
    font-weight: 600;
}

/* Steps Indicator */
.step-container {
    padding: 10px 15px;
    border-radius: 8px;
    background-color: rgba(255, 255, 255, 0.03);
    margin-bottom: 8px;
    border-left: 4px solid #475569;
}

.step-active {
    border-left-color: #6366f1;
    background-color: rgba(99, 102, 241, 0.05);
}

.step-done {
    border-left-color: #22c55e;
}

/* Custom chat bubble layout */
.chat-bubble {
    padding: 12px 16px;
    border-radius: 12px;
    margin-bottom: 10px;
    line-height: 1.5;
}

.chat-interviewer {
    background-color: rgba(99, 102, 241, 0.1);
    border: 1px solid rgba(99, 102, 241, 0.2);
    border-top-left-radius: 2px;
}

.chat-candidate {
    background-color: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-top-right-radius: 2px;
}

</style>
""", unsafe_allow_html=True)

# Initialize Session States
if "step" not in st.session_state:
    st.session_state.step = "UPLOAD"
if "candidate_id" not in st.session_state:
    st.session_state.candidate_id = None
if "parsed_profile" not in st.session_state:
    st.session_state.parsed_profile = None
if "recommended_roles" not in st.session_state:
    st.session_state.recommended_roles = []
if "selected_role" not in st.session_state:
    st.session_state.selected_role = None
if "interview_qas" not in st.session_state:
    st.session_state.interview_qas = []
if "current_question" not in st.session_state:
    st.session_state.current_question = ""
if "selected_model" not in st.session_state:
    st.session_state.selected_model = None

# Initialize database
@st.cache_resource
def get_db():
    db = TalentDB()
    db.seed_roles()
    return db

db = get_db()

# Sidebar: Configuration, status & navigation
with st.sidebar:
    st.image("https://img.icons8.com/isometric/100/null/artificial-intelligence.png", width=60)
    st.markdown("### Talent AI Controller")
    st.markdown("---")
    
    # Model Selection from running instances
    st.markdown("#### LLM Model Settings")
    available_models = llm_client.get_available_models()
    import config
    default_idx = available_models.index(config.LLM_MODEL) if config.LLM_MODEL in available_models else 0
    selected_model = st.selectbox(
        "Active LLM Model",
        options=available_models,
        index=default_idx
    )
    st.session_state.selected_model = selected_model
    
    st.markdown("---")
    st.markdown("#### Process Progress")
    
    # Render steps dynamically based on state
    steps = [
        ("UPLOAD", "Upload Resume"),
        ("SELECT_ROLE", "Select Job Role"),
        ("INTERVIEW", "LLM Technical Interview"),
        ("PREF_FORM", "Submit Preferences"),
        ("REPORT", "Evaluation Report")
    ]
    
    current_step_idx = next(i for i, (s, _) in enumerate(steps) if s == st.session_state.step)
    
    for i, (s, label) in enumerate(steps):
        if i < current_step_idx:
            # Done
            st.markdown(f'<div class="step-container step-done">✅ <b>{label}</b></div>', unsafe_allow_html=True)
        elif i == current_step_idx:
            # Active
            st.markdown(f'<div class="step-container step-active">⚡ <b>{label}</b></div>', unsafe_allow_html=True)
        else:
            # Future
            st.markdown(f'<div class="step-container">⚪ {label}</div>', unsafe_allow_html=True)
            
    st.markdown("---")
    
    # Database status
    try:
        db.client.admin.command('ping')
        db_status = "💚 Connected"
    except Exception:
        db_status = "❤️ Disconnected"
    st.metric("MongoDB Status", db_status)

# ----------------- STEP 1: UPLOAD RESUME -----------------
if st.session_state.step == "UPLOAD":
    st.markdown('<div class="main-title">Talent Acquisition Platform</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">Upload your resume to parse skills, match matching roles, and begin a dynamic interview.</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("Upload Candidate Resume")
        uploaded_file = st.file_uploader(
            "Supported formats: PDF, TXT (Max size 10MB)",
            type=["pdf", "txt"],
            help="Your resume will be processed using local secure parsers."
        )
        
        if uploaded_file is not None:
            # Enforce 10MB limit
            file_size_mb = len(uploaded_file.getvalue()) / (1024 * 1024)
            if file_size_mb > 10.0:
                st.error("File exceeds the 10MB size limit. Please upload a smaller file.")
            else:
                if st.button("Process & Match Roles", type="primary"):
                    with st.spinner("Reading resume contents and extracting skills..."):
                        # Save temporarily
                        file_ext = uploaded_file.name.split(".")[-1]
                        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file_ext}") as tmp:
                            tmp.write(uploaded_file.getvalue())
                            tmp_path = tmp.name
                            
                        try:
                            # 1. Extract text and parse profile details
                            raw_text, parsed_profile = parser.process_resume(
                                tmp_path, 
                                file_ext, 
                                model_name=st.session_state.selected_model
                            )
                            
                            # Clean temp file
                            os.unlink(tmp_path)
                            
                            st.session_state.parsed_profile = parsed_profile
                            
                            # 2. Match with jobs in database using BERT/Cosine similarity
                            all_roles = db.get_all_roles()
                            
                            # Make sure roles exist
                            if not all_roles:
                                st.error("No job roles found in database. Seed job_role.json first.")
                            else:
                                with st.spinner("Calculating semantic match with job roles..."):
                                    candidate_skills = parsed_profile.get("skills", [])
                                    recommended = matcher.recommend_roles(candidate_skills, all_roles)
                                    st.session_state.recommended_roles = recommended
                                    
                                    # 3. Create candidate entry in MongoDB
                                    cand_id = db.create_candidate(parsed_profile, raw_text)
                                    st.session_state.candidate_id = cand_id
                                    
                                    # Transition to role selection
                                    st.session_state.step = "SELECT_ROLE"
                                    st.rerun()
                        except Exception as e:
                            st.error(f"Error processing resume: {str(e)}")
                            if os.path.exists(tmp_path):
                                os.unlink(tmp_path)

    with col2:
        st.markdown("""
        ### How it works
        1. **Resume Processing**: We parse clean text using `pdfplumber` and identify candidate name, email, experience, and key technical skills.
        2. **Semantic Matching**: Candidate skills are matched against database job roles using **BERT Sentence Embeddings**. High-importance skills carry higher weights.
        3. **LLM Technical Interview**: The AI conducts a 5-question technical interview tailored dynamically to your profile.
        4. **Detailed Report**: A full scoring breakdown is saved to MongoDB.
        """)

# ----------------- STEP 2: SELECT ROLE -----------------
elif st.session_state.step == "SELECT_ROLE":
    st.markdown('<div class="main-title">Select Job Role</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">Review your parsed profile details and choose which job role to interview for.</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("Parsed Profile")
        profile = st.session_state.parsed_profile
        
        st.text_input("Name", value=profile.get("name", ""), disabled=True)
        st.text_input("Email", value=profile.get("email", ""), disabled=True)
        st.text_input("Phone", value=profile.get("phone", ""), disabled=True)
        st.text_input("Current Location", value=profile.get("current_location", ""), disabled=True)
        st.number_input("Years of Experience", value=float(profile.get("years_of_experience") or 0.0), disabled=True)
        
        st.markdown("**Skills Found:**")
        st.write(", ".join(profile.get("skills", [])) or "None")
        
    with col2:
        st.subheader("Recommended Job Roles (Top 5 Matches)")
        
        for idx, rec in enumerate(st.session_state.recommended_roles):
            role_name = rec["job_role"]
            score = rec["match_score"]
            desc = rec["job_description"]
            skills_req = rec["skills"]
            
            with st.container():
                st.markdown(f"""
                <div class="role-card">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <h4 style="margin: 0; color: #818cf8;">{role_name}</h4>
                        <span class="score-badge">Match: {score}%</span>
                    </div>
                    <p style="font-size: 0.9rem; margin-top: 10px; color: #cbd5e1;">{desc[:250]}...</p>
                    <div style="font-size: 0.8rem; color: #94a3b8;">
                        <b>Key Skills:</b> {", ".join([s.get("skill_name", "") for s in skills_req])}
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                if st.button(f"Apply & Start Interview - {role_name}", key=f"btn_{idx}"):
                    # Update database with chosen role
                    db.update_candidate_role(st.session_state.candidate_id, role_name)
                    st.session_state.selected_role = role_name
                    
                    # Generate the first interview question
                    with st.spinner("Generating your first question..."):
                        first_q = interview.generate_next_question(
                            role_name, 
                            desc, 
                            profile.get("skills", []), 
                            profile.get("projects", []), 
                            [], 
                            model_name=st.session_state.selected_model
                        )
                        st.session_state.current_question = first_q
                        # Save the first question in database
                        db.add_interview_qa(st.session_state.candidate_id, first_q)
                        st.session_state.interview_qas.append({"question": first_q, "answer": ""})
                        
                    st.session_state.step = "INTERVIEW"
                    st.rerun()

# ----------------- STEP 3: INTERVIEW -----------------
elif st.session_state.step == "INTERVIEW":
    role_name = st.session_state.selected_role
    role_data = db.get_role_by_name(role_name)
    role_desc = role_data.get("job_description", "") if role_data else ""
    
    st.markdown(f'<div class="main-title">Interview: {role_name}</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">Answer each question professionally. Your answers determine the follow-up questions.</div>', unsafe_allow_html=True)
    
    # Progress Bar
    q_count = len(st.session_state.interview_qas)
    progress_val = q_count / 5.0
    st.progress(progress_val, text=f"Question {q_count} of 5")
    
    # Chat display container
    st.write("### Conversation")
    
    # Render previous Q&As
    for i, qa in enumerate(st.session_state.interview_qas):
        # Render Interviewer Question
        st.markdown(f"""
        <div class="chat-bubble chat-interviewer">
            <b>Interviewer (AI)</b><br/>{qa['question']}
        </div>
        """, unsafe_allow_html=True)
        
        # Render Candidate Answer
        if qa.get("answer"):
            st.markdown(f"""
            <div class="chat-bubble chat-candidate">
                <b>You</b><br/>{qa['answer']}
            </div>
            """, unsafe_allow_html=True)
            
    # Form for entering the current answer
    # Only render input for the active question (which is the last one in the history)
    last_qa = st.session_state.interview_qas[-1]
    
    if not last_qa.get("answer"):
        with st.form("answer_form", clear_on_submit=True):
            user_answer = st.text_area("Your Answer:", height=150, placeholder="Type your technical response here...")
            submitted = st.form_submit_button("Submit Answer")
            
            if submitted:
                if not user_answer.strip():
                    st.warning("Please provide a response before submitting.")
                else:
                    # 1. Update session state and database with candidate response
                    st.session_state.interview_qas[-1]["answer"] = user_answer
                    db.update_last_qa_answer(st.session_state.candidate_id, user_answer)
                    
                    # 2. Check if we need to ask another question
                    if q_count < 5:
                        with st.spinner("Evaluating response and formulating next question..."):
                            next_q = interview.generate_next_question(
                                role_name,
                                role_desc,
                                st.session_state.parsed_profile.get("skills", []),
                                st.session_state.parsed_profile.get("projects", []),
                                st.session_state.interview_qas,
                                model_name=st.session_state.selected_model
                            )
                            # Save next question to database and state
                            db.add_interview_qa(st.session_state.candidate_id, next_q)
                            st.session_state.interview_qas.append({"question": next_q, "answer": ""})
                            st.session_state.current_question = next_q
                        st.rerun()
                    else:
                        # 5 questions finished, move to preferences collection
                        st.session_state.step = "PREF_FORM"
                        st.rerun()
    else:
        st.info("Interview conversation completed. Transitioning to preferences details.")

# ----------------- STEP 4: PREFERENCES FORM -----------------
elif st.session_state.step == "PREF_FORM":
    st.markdown('<div class="main-title">Preferences Details</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">Almost done! Provide your job preferences to complete the assessment.</div>', unsafe_allow_html=True)
    
    with st.form("pref_form"):
        st.subheader("Candidate Preferences")
        
        salary = st.text_input("Salary Expectation (e.g. $100,000 / 12 LPA)", placeholder="Expected CTC")
        relocation = st.radio("Are you open to relocation?", ["Yes", "No", "Negotiable"], index=0)
        wfh = st.selectbox("Workplace Preference", ["Remote", "Hybrid", "On-site"], index=1)
        curr_loc = st.text_input("Current Location (City, Country)", placeholder="e.g. Mumbai, India")
        
        submitted = st.form_submit_button("Submit & Generate Report")
        
        if submitted:
            if not salary.strip() or not curr_loc.strip():
                st.warning("Please fill out all preference fields.")
            else:
                preferences = {
                    "salary_expectation": salary,
                    "relocation_ok": relocation,
                    "wfh_preference": wfh,
                    "current_location": curr_loc
                }
                
                # Save to MongoDB
                db.save_preferences(st.session_state.candidate_id, preferences)
                
                # Trigger LLM Evaluation Report
                with st.spinner("AI evaluating transcript and scoring your interview (may take a moment)..."):
                    evaluation = interview.evaluate_candidate(
                        st.session_state.parsed_profile.get("name", "Candidate"),
                        st.session_state.selected_role,
                        st.session_state.interview_qas,
                        model_name=st.session_state.selected_model
                    )
                    # Save evaluation report to MongoDB
                    db.save_evaluation(st.session_state.candidate_id, evaluation)
                    
                st.session_state.step = "REPORT"
                st.rerun()

# ----------------- STEP 5: EVALUATION REPORT -----------------
elif st.session_state.step == "REPORT":
    st.markdown('<div class="main-title">Candidate Evaluation Report</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">The complete interview profile has been compiled and safely recorded in MongoDB.</div>', unsafe_allow_html=True)
    
    # Retrieve current candidate profile & evaluation details from DB
    candidate = db.get_candidate(st.session_state.candidate_id)
    eval_report = candidate.get("evaluation", {})
    personal = candidate.get("personal_info", {})
    prefs = candidate.get("preferences", {})
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("Summary Card")
        
        # Grading and decision badges
        rec = eval_report.get("recommendation", "Hire")
        rec_color = "#22c55e" if "strong" in rec.lower() or "hire" in rec.lower() and "no" not in rec.lower() else "#ef4444"
        
        st.markdown(f"""
        <div style="background: rgba(30, 41, 59, 0.5); padding: 20px; border-radius: 12px; border: 1px solid rgba(255, 255, 255, 0.1);">
            <h3 style="margin-top:0;">{personal.get('name', 'Candidate')}</h3>
            <p><b>Role Applied:</b> {candidate.get('selected_role')}</p>
            <p><b>Decision Recommendation:</b> <span style="color: {rec_color}; font-weight: 700;">{rec}</span></p>
            <hr style="border-color: rgba(255,255,255,0.1);"/>
            <h4>Overall Assessment Scores</h4>
            <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                <span>Technical Score:</span>
                <b>{eval_report.get('technical_score', 0.0)}%</b>
            </div>
            <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                <span>Soft Skills Score:</span>
                <b>{eval_report.get('soft_skills_score', 0.0)}%</b>
            </div>
            <div style="display: flex; justify-content: space-between; margin-bottom: 8px; font-size: 1.1rem; color: #818cf8;">
                <span>Final Match Rating:</span>
                <b>{eval_report.get('final_score', 0.0)}%</b>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        st.write("")
        st.subheader("Declared Preferences")
        st.markdown(f"""
        - **Salary Expectation**: {prefs.get('salary_expectation')}
        - **Relocation**: {prefs.get('relocation_ok')}
        - **WFH Preference**: {prefs.get('wfh_preference')}
        - **Current Location**: {prefs.get('current_location')}
        """)
        
    with col2:
        st.subheader("Evaluation Details")
        
        with st.expander("📝 Executive Strengths & Gaps Summaries", expanded=True):
            st.markdown(f"**Technical Capabilities Summary:**\n{eval_report.get('technical_summary', '')}")
            st.write("")
            st.markdown(f"**Communication & Soft Skills Summary:**\n{eval_report.get('soft_skill_summary', '')}")
            
        st.subheader("Transcript Breakdown & Question Scores")
        
        detailed_feedback = eval_report.get("detailed_feedback", [])
        
        for item in detailed_feedback:
            q_num = item.get("question_number", 0)
            question = item.get("question", "")
            answer = item.get("answer", "")
            score = item.get("score", 0.0)
            feedback = item.get("feedback", "")
            
            with st.expander(f"Question {q_num}: {question[:80]}... - Score: {score}%", expanded=False):
                st.markdown(f"**Question:** {question}")
                st.markdown(f"**Candidate Answer:** *{answer}*")
                st.markdown(f"**Score:** `{score}%`")
                st.markdown(f"**AI Assessor Feedback:** {feedback}")
                
        if st.button("Start New Assessment", type="primary"):
            # Reset session states
            for key in ["step", "candidate_id", "parsed_profile", "recommended_roles", "selected_role", "interview_qas", "current_question"]:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()
