import streamlit as st
import requests
import json
import pdfplumber
import os
from datetime import datetime

# =====================================================
# PAGE CONFIG
# =====================================================

st.set_page_config(
    page_title="Airtel AI Recruitment System",
    page_icon="📡",
    layout="wide"
)

# =====================================================
# CONFIGURATION
# =====================================================

API_URL = "http://llm01.cmi.rebhu.in:11434/api/chat"
MODEL_NAME = "gemma4:e2b"

TOTAL_QUESTIONS = 5

# =====================================================
# JOB ROLE DATABASE
# =====================================================

JOB_ROLES = {
  "Fibre Optic Technician": [
    "Fiber cable installation",
    "Broadband connection setup",
    "FTTH connection",
    "Router installation",
    "ONT/modem setup",
    "Internet troubleshooting",
    "Cable fault checking",
    "Basic fiber splicing",
    "OTDR testing assistance",
    "Fiber wire joining",
    "Pole to home cable connection",
    "Underground cable laying",
    "LAN cable crimping",
    "RJ45 connector fixing",
    "Internet speed testing",
    "Signal loss checking",
    "Network device checking",
    "Basic switch configuration",
    "Basic router configuration",
    "Electrical safety practices",
    "Use of hand tools",
    "Field maintenance work",
    "Customer issue handling",
    "Preventive maintenance",
    "Telecom equipment handling"
  ],

  "Network Technician": [
    "LAN cable installation",
    "Router installation",
    "Switch installation",
    "Internet troubleshooting",
    "WiFi setup",
    "LAN/WAN setup",
    "TCP/IP basics",
    "RJ45 crimping",
    "Cable testing",
    "Network device checking",
    "Basic switch configuration",
    "Basic router configuration",
    "IP address configuration",
    "Network fault checking",
    "Broadband troubleshooting",
    "Patch panel handling",
    "Hardware installation",
    "Ping and traceroute testing",
    "Customer support handling",
    "Preventive maintenance",
    "Wireless access point setup",
    "Basic firewall understanding",
    "Cisco device basics",
    "Network monitoring basics"
  ],

  "Network Configuration Engineer": [
    "Router configuration",
    "Switch configuration",
    "VLAN setup",
    "Routing and switching",
    "OSPF configuration",
    "BGP basics",
    "Firewall configuration",
    "Cisco device management",
    "Network security basics",
    "IP subnetting",
    "LAN/WAN configuration",
    "Access control list setup",
    "Network troubleshooting",
    "Command line interface usage",
    "DHCP configuration",
    "DNS configuration",
    "VPN basics",
    "Wireless controller basics",
    "Network monitoring",
    "Packet analysis",
    "TCP/IP networking",
    "Cisco IOS commands",
    "Switch port configuration",
    "Enterprise network maintenance",
    "Backup and restore network configuration"
  ],

  "Fault Management Engineer": [
    "Network fault detection",
    "Cable cut identification",
    "Internet outage troubleshooting",
    "Fiber fault checking",
    "Network monitoring",
    "Incident handling",
    "Alarm monitoring",
    "Basic OTDR analysis",
    "Troubleshooting connectivity issues",
    "Router and switch checking",
    "LAN/WAN troubleshooting",
    "Fault ticket management",
    "Preventive maintenance",
    "Signal loss checking",
    "PRTG monitoring basics",
    "SolarWinds basics",
    "Escalation handling",
    "Root cause analysis",
    "Service restoration support",
    "Downtime management",
    "Field coordination",
    "Basic telecom infrastructure knowledge",
    "Network diagnostics",
    "Technical support handling",
    "Emergency fault response"
  ]
}

# =====================================================
# SESSION STATE
# =====================================================

default_states = {
    "page": "upload",
    "resume_processed": False,
    "resume_text": "",
    "candidate_info": {},
    "matched_role": "",
    "match_scores": {},
    "chat_history": [],
    "question_count": 0,
    "evaluation": {},
    "total_input_tokens": 0,
    "total_output_tokens": 0,
    "page_input_tokens": {},
    "page_output_tokens": {}
}

for key, value in default_states.items():

    if key not in st.session_state:
        st.session_state[key] = value

# =====================================================
# TOKEN COUNT FUNCTION
# =====================================================

def count_tokens(text):

    if not text:
        return 0

    return len(text.split())

# =====================================================
# LLM FUNCTION
# =====================================================

def call_llm(messages, temperature=0.5, json_mode=False):

    input_text = ""

    for msg in messages:

        input_text += msg.get("content", "") + " "

    input_tokens = count_tokens(input_text)

    payload = {
        "model": MODEL_NAME,
        "messages": messages,
        "stream": False,
        "options": {
            "temperature": temperature
        }
    }

    if json_mode:
        payload["format"] = "json"

    try:

        response = requests.post(
            API_URL,
            json=payload,
            timeout=120
        )

        result = response.json()

        output_text = result.get(
            "message",
            {}
        ).get(
            "content",
            ""
        )

        output_tokens = count_tokens(output_text)

        current_page = st.session_state.page

        # =================================================
        # TOTAL TOKENS
        # =================================================

        st.session_state.total_input_tokens += input_tokens
        st.session_state.total_output_tokens += output_tokens

        # =================================================
        # PAGE TOKENS
        # =================================================

        if current_page not in st.session_state.page_input_tokens:

            st.session_state.page_input_tokens[current_page] = 0

        if current_page not in st.session_state.page_output_tokens:

            st.session_state.page_output_tokens[current_page] = 0

        st.session_state.page_input_tokens[current_page] += input_tokens

        st.session_state.page_output_tokens[current_page] += output_tokens

        return output_text

    except Exception as e:

        st.error(f"LLM API Error: {e}")

        return None

# =====================================================
# MATCHING FUNCTION
# =====================================================

def calculate_match_scores(candidate_skills):

    scores = {}

    candidate_skills_lower = [
        skill.lower()
        for skill in candidate_skills
    ]

    for role, role_skills in JOB_ROLES.items():

        matched = 0

        for skill in role_skills:

            if any(
                skill.lower() in candidate_skill
                for candidate_skill in candidate_skills_lower
            ):
                matched += 1

        score = int(
            (matched / len(role_skills)) * 100
        )

        scores[role] = score

    return scores

# =====================================================
# SAVE INTERVIEW DATA
# =====================================================

def save_interview_data():

    os.makedirs("candidate_records", exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    filename = f"candidate_records/interview_{timestamp}.json"

    data = {
        "candidate_information": st.session_state.candidate_info,
        "matched_role": st.session_state.matched_role,
        "role_match_scores": st.session_state.match_scores,
        "chat_history": st.session_state.chat_history,
        "evaluation": st.session_state.evaluation,
        "total_input_tokens": st.session_state.total_input_tokens,
        "total_output_tokens": st.session_state.total_output_tokens
    }

    with open(filename, "w") as f:
        json.dump(data, f, indent=4)

# =====================================================
# SIDEBAR
# =====================================================

st.sidebar.title("Airtel Recruitment Workflow")

steps = [
    "1. Upload Resume",
    "2. AI Interview",
    "3. Result"
]

page_map = {
    "upload": 0,
    "interview": 1,
    "evaluation": 2
}

for i, step in enumerate(steps):

    if i == page_map[st.session_state.page]:

        st.sidebar.markdown(
            f"**👉 {step}**"
        )

    else:

        st.sidebar.markdown(
            f"<span style='color:gray'>{step}</span>",
            unsafe_allow_html=True
        )

# =====================================================
# TOKEN DISPLAY
# =====================================================

st.sidebar.divider()

st.sidebar.subheader("Token Usage")

current_page = st.session_state.page

input_tokens = st.session_state.page_input_tokens.get(
    current_page,
    0
)

output_tokens = st.session_state.page_output_tokens.get(
    current_page,
    0
)

st.sidebar.write(
    f"Page Input Tokens: {input_tokens}"
)

st.sidebar.write(
    f"Page Output Tokens: {output_tokens}"
)

st.sidebar.divider()

st.sidebar.write(
    f"Total Input Tokens: {st.session_state.total_input_tokens}"
)

st.sidebar.write(
    f"Total Output Tokens: {st.session_state.total_output_tokens}"
)

# =====================================================
# RESET
# =====================================================

if st.sidebar.button("Reset"):

    for key in list(st.session_state.keys()):
        del st.session_state[key]

    st.rerun()

# =====================================================
# PAGE 1 — RESUME UPLOAD
# =====================================================

if st.session_state.page == "upload":

    st.title("📡 Airtel AI Recruitment System")

    uploaded_file = st.file_uploader(
        "Upload Resume",
        type=["pdf", "txt"]
    )

    if uploaded_file and not st.session_state.resume_processed:

        if st.button("Process Resume"):

            resume_text = ""

            with st.spinner("Reading Resume..."):

                if uploaded_file.type == "text/plain":

                    resume_text = uploaded_file.read().decode("utf-8")

                elif uploaded_file.type == "application/pdf":

                    try:

                        with pdfplumber.open(uploaded_file) as pdf:

                            for page in pdf.pages:

                                extracted = page.extract_text()

                                if extracted:
                                    resume_text += extracted + "\n"

                    except Exception as e:

                        st.error(f"PDF Parsing Error: {e}")
                        st.stop()

            st.session_state.resume_text = resume_text

            extraction_prompt = """
            You are an AI recruitment assistant.

            Extract:

            - Name
            - Email
            - Phone
            - Total Experience
            - Relevant Experience
            - Skills
            - Projects

            Return ONLY valid JSON.
            """

            with st.spinner("Analyzing Resume..."):

                response = call_llm(
                    [
                        {
                            "role": "system",
                            "content": extraction_prompt
                        },
                        {
                            "role": "user",
                            "content": resume_text
                        }
                    ],
                    temperature=0.1,
                    json_mode=True
                )

            if response:

                try:

                    candidate_info = json.loads(response)

                    st.session_state.candidate_info = candidate_info

                    candidate_skills = candidate_info.get(
                        "Skills",
                        []
                    )

                    match_scores = calculate_match_scores(
                        candidate_skills
                    )

                    st.session_state.match_scores = match_scores

                    best_role = max(
                        match_scores,
                        key=match_scores.get
                    )

                    st.session_state.matched_role = best_role

                    st.session_state.resume_processed = True

                    st.rerun()

                except Exception as e:

                    st.error(f"JSON Parsing Error: {e}")

    if st.session_state.resume_processed:

        st.success(
            "Resume Processed Successfully"
        )

        st.write(
            "Your AI technical interview is ready."
        )

        if st.button("Start AI Interview"):

            candidate_info = st.session_state.candidate_info

            skills = candidate_info.get(
                "Skills",
                []
            )

            projects = candidate_info.get(
                "Projects",
                []
            )

            matched_role = st.session_state.matched_role

            system_prompt = f"""
            You are a recruiter at Airtel.
            Candidate Matched Role:
            {matched_role}
            Candidate Skills:
            {skills}
            Candidate Projects:
            {projects}
            Rules:
            1. Ask exactly {TOTAL_QUESTIONS} questions.
            2. Ask only one question at a time. The next question must be asked only after the candidate answers the current question. If the candidate’s answer is incomplete, unclear, weak, or not satisfactory, ask relevant follow-up questions before moving to the next main question.
            3. Understand the selected job role properly from both a practical and logical perspective. Clearly understand the actual responsibilities of the role and the minimum educational qualification realistically required to perform that job. Based on this understanding, generate appropriate interview questions.
            4. If the job role requires strong theoretical understanding along with practical skills, ask questions that evaluate conceptual clarity, technical understanding, and practical application of important concepts. 
               If the job role mainly requires practical field skills and does not require advanced theoretical education or a degree, focus more on practical troubleshooting, real-world work situations, installation steps, customer handling, and technical tasks commonly performed during the job.
            Example:
            - A househelp does not need to know the chemical formula of detergent, but should know how clothes should be washed properly.
            - A Data Scientist should possess theoretical knowledge, conceptual clarity, educational background, and practical implementation skills.
            5. Analyze the educational qualification of the candidate and adjust the difficulty level accordingly. If a candidate has a strong educational background but has applied for a role that does not require advanced theoretical knowledge, do not ask unnecessarily difficult or highly academic questions unless genuinely relevant to the job role.
            6. Ask all interview questions in simple, clear, and natural English language that is easy for the candidate to understand.
            7. The interview should feel practical, realistic, and relevant to real-world job responsibilities instead of sounding like an academic examination.
            """

            st.session_state.chat_history = [
                {
                    "role": "system",
                    "content": system_prompt
                }
            ]

            st.session_state.page = "interview"

            st.rerun()

# =====================================================
# PAGE 2 — INTERVIEW
# =====================================================

elif st.session_state.page == "interview":

    st.title("💬 AI Technical Interview")

    progress = min(
        st.session_state.question_count / TOTAL_QUESTIONS,
        1.0
    )

    st.progress(progress)

    if st.session_state.question_count < TOTAL_QUESTIONS:

        st.write(
            f"Question {st.session_state.question_count + 1} of {TOTAL_QUESTIONS}"
        )

    else:

        st.write("Interview Completed")

    # =====================================================
    # FIRST QUESTION
    # =====================================================

    if len(st.session_state.chat_history) == 1:

        with st.spinner("Generating First Question..."):

            first_question = call_llm(
                st.session_state.chat_history
            )

            st.session_state.chat_history.append(
                {
                    "role": "assistant",
                    "content": first_question
                }
            )

            st.rerun()

    # =====================================================
    # DISPLAY CHAT
    # =====================================================

    for msg in st.session_state.chat_history:

        if msg["role"] != "system":

            with st.chat_message(msg["role"]):

                st.markdown(msg["content"])

    # =====================================================
    # USER INPUT
    # =====================================================

    if st.session_state.question_count < TOTAL_QUESTIONS:

        user_input = st.chat_input(
            "Type your answer..."
        )

        if user_input:

            st.session_state.chat_history.append(
                {
                    "role": "user",
                    "content": user_input
                }
            )

            st.session_state.question_count += 1

            if st.session_state.question_count < TOTAL_QUESTIONS:

                with st.spinner("Generating Next Question..."):

                    next_question = call_llm(
                        st.session_state.chat_history
                    )

                    st.session_state.chat_history.append(
                        {
                            "role": "assistant",
                            "content": next_question
                        }
                    )

            st.rerun()

    # =====================================================
    # GENERATE RESULT
    # =====================================================

    if st.session_state.question_count >= TOTAL_QUESTIONS:

        if st.button("Generate Result"):

            st.session_state.page = "evaluation"

            st.rerun()

# =====================================================
# PAGE 3 — EVALUATION
# =====================================================

elif st.session_state.page == "evaluation":

    st.title("📊 Interview Result")

    if not st.session_state.evaluation:

        evaluation_prompt = f"""
        You are a senior Airtel technical hiring evaluator.
        Evaluate the candidate based on the complete interview conversation.
        IMPORTANT RULES:
        1. Give realistic scores.
        2. Scores must strictly be between 1 and 10.
        3. Output ONLY valid JSON.
        4. Do not add explanations outside JSON.
        5. Overall score must reflect complete interview performance.
        6. Weak answers should reduce scores.
        7. Practical job roles should be evaluated more on practical understanding.

        Return JSON in EXACT format:

        {{
            "Technical_Knowledge": 0,
            "Problem_Solving": 0,
            "Communication": 0,
            "Confidence": 0,
            "Practical_Understanding": 0,
            "Overall_Rating": 0,
            "Internal_Summary": ""
        }}
        """

        messages = st.session_state.chat_history.copy()

        messages.append(
            {
                "role": "user",
                "content": evaluation_prompt
            }
        )

        with st.spinner("Evaluating Interview..."):

            response = call_llm(
                messages,
                temperature=0.1,
                json_mode=True
            )

        if response:

            try:

                evaluation = json.loads(response)

                required_fields = [
                    "Technical_Knowledge",
                    "Problem_Solving",
                    "Communication",
                    "Confidence",
                    "Practical_Understanding",
                    "Overall_Rating"
                ]

                valid = True

                for field in required_fields:

                    if field not in evaluation:
                        valid = False

                if not valid:

                    st.error("Invalid evaluation response from model.")

                    st.stop()

                st.session_state.evaluation = evaluation

                save_interview_data()

            except Exception as e:

                st.error(f"Evaluation Parsing Error: {e}")

    evaluation = st.session_state.evaluation

    # =====================================================
    # DISPLAY FINAL SCORE
    # =====================================================

    final_score = evaluation.get(
        "Overall_Rating",
        0
    )

    try:

        final_score = int(final_score)

    except:

        final_score = 0

    st.metric(
        "Final Interview Score",
        f"{final_score}/10"
    )

    st.progress(final_score / 10)

    st.success(
        "Thank you for completing the interview."
    )