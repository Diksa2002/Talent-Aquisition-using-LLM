import json
import llm_client

def generate_next_question(job_role, job_description, candidate_skills, candidate_projects, qas_history, model_name=None):
    """
    Formulates the next interview question based on job role details, candidate skills, candidate projects,
    and previous chat history. Ensures a conversational and context-aware flow.
    Strictly aligns questions with the target job role and ignores non-matching resume details.
    """
    TOTAL_QUESTIONS = 5
    matched_role = job_role
    skills = ', '.join(candidate_skills) if candidate_skills else 'Not specified'
    projects = ', '.join(candidate_projects) if candidate_projects else 'Not specified'
    
    system_prompt = f"""
            You are an expert technical interviewer and recruiter.
            
            TARGET JOB ROLE (ABSOLUTE SOURCE OF TRUTH):
            {matched_role}
            Job Role Description:
            {job_description}
            
            CANDIDATE RESUME SKILLS:
            {skills}
            CANDIDATE RESUME PROJECTS:
            {projects}
            
            CRITICAL RULES:
            1. THE TARGET JOB ROLE IS THE ABSOLUTE SOURCE OF TRUTH.
               - You MUST ask questions ONLY relevant to the target job role: '{matched_role}'.
               - If candidate resume skills or projects are UNRELATED to '{matched_role}' (e.g. Python or Machine Learning skills listed for a Financial Accountant or Store Manager role), YOU MUST COMPLETELY IGNORE THEM.
               - DO NOT ask programming or tech stack questions unless '{matched_role}' explicitly requires them!
            2. Ask exactly {TOTAL_QUESTIONS} questions, one at a time.
            3. Evaluate response quality before generating the next question. If the candidate's previous answer was incomplete, unclear, or weak, ask a relevant follow-up question.
            4. Adjust question difficulty appropriately for the practical domain of '{matched_role}'. Focus on real-world troubleshooting, field scenarios, core domain knowledge, and practical execution.
            5. Write all questions in simple, clear, professional English.
            6. Output ONLY the direct interview question text. No intro/outro fillers, conversational logs, or headers.
            """
    
    messages = [{"role": "system", "content": system_prompt}]
    
    # Rebuild conversation history
    for qa in qas_history:
        messages.append({"role": "assistant", "content": qa["question"]})
        if qa.get("answer"):
            messages.append({"role": "user", "content": qa["answer"]})
            
    # If no history yet, ask the candidate to begin
    if not qas_history:
        messages.append({"role": "user", "content": "Let's start the interview. Ask your first question."})
    else:
        messages.append({"role": "user", "content": "Ask the next relevant follow-up question based on our discussion."})
        
    try:
        question = llm_client.query_llm(messages, temperature=0.7, model_name=model_name)
        return question.strip()
    except Exception as e:
        print(f"Error generating interview question: {str(e)}")
        q_idx = len(qas_history)
        
        # General fallbacks aligned with target job role
        general_fallbacks = [
            f"Could you describe a challenging scenario you experienced as a {job_role} and explain how you handled it?",
            f"How do you typically approach troubleshooting or solving complex operational problems as a {job_role}?",
            f"Can you share an instance where you had to adapt quickly to unexpected changes in your role as a {job_role}?",
            f"How do you maintain high quality standards while meeting tight deadlines in a {job_role} position?",
            f"What core skills or best practices do you consider essential to succeed as a {job_role}?"
        ]
        return general_fallbacks[q_idx % len(general_fallbacks)]

def evaluate_candidate(candidate_name, job_role, qas_history, model_name=None):
    """
    Reviews the candidate transcript and generates a graded evaluation scoring card.
    Strictly penalizes gibberish ('xyz', 'asdf', off-topic noise) and skipped questions with 0.0 scores.
    """
    system_prompt = (
        "You are an expert technical interviewer and talent assessor. Your job is to review the "
        "provided interview transcript and generate a structured grading scorecard.\n\n"
        "STRICT EVALUATION CRITERIA:\n"
        "1. GIBBERISH / NONSENSE / OFF-TOPIC ANSWERS: If an answer contains nonsense (e.g., 'xyz', 'abc', 'asdf', random text), "
        "empty response, or completely off-topic noise, YOU MUST AWARD technical_score = 0.0 AND soft_skills_score = 0.0.\n"
        "2. SKIPPED ANSWERS: If the answer is 'Skipped', AWARD technical_score = 0.0 AND soft_skills_score = 0.0.\n"
        "3. SHORT / SURFACE ANSWERS: If an answer is extremely short (1-3 generic words like 'yes', 'good', 'i know'), "
        "the technical_score MUST NOT exceed 30.0 and soft_skills_score MUST NOT exceed 20.0.\n"
        "4. INDEPENDENT METRICS: Evaluate technical accuracy and soft skills communication structures independently. "
        "Do NOT assign identical scores unless genuinely justified by the candidate's performance.\n\n"
        "You MUST return ONLY a valid JSON object. Do not include markdown block wrapping (```json), "
        "notes, or explanations. Conform strictly to this schema:\n"
        "{\n"
        "  \"detailed_feedback\": [\n"
        "    {\n"
        "      \"question_number\": 1,\n"
        "      \"question\": \"The question asked\",\n"
        "      \"answer\": \"The candidate's response\",\n"
        "      \"technical_score\": 0.0 to 100.0 (float, strict technical correctness),\n"
        "      \"soft_skills_score\": 0.0 to 100.0 (float, communication clarity & structure),\n"
        "      \"feedback\": \"Constructive feedback for this specific response\"\n"
        "    }\n"
        "  ],\n"
        "  \"technical_summary\": \"Detailed overview of technical strengths, core gaps, and domain mastery.\",\n"
        "  \"soft_skill_summary\": \"Assessment of structure, vocabulary, confidence, and articulation.\",\n"
        "  \"recommendation\": \"Strong Hire / Hire / No Hire\"\n"
        "}\n\n"
        "Analyze the depth, correctness, and relevance of each answer carefully. Be objective, strict, and fair."
    )
    
    # Format the transcript text
    transcript_lines = []
    for i, qa in enumerate(qas_history):
        q = qa.get("question", "")
        a = qa.get("answer", "")
        transcript_lines.append(f"Q{i+1}: {q}\nA{i+1}: {a}")
        
    transcript_text = "\n\n".join(transcript_lines)
    
    user_prompt = (
        f"Candidate Name: {candidate_name}\n"
        f"Target Role: {job_role}\n\n"
        f"Interview Transcript:\n{transcript_text}"
    )
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]
    
    try:
        response_content = llm_client.query_llm(messages, temperature=0.1, json_mode=True, model_name=model_name)
        
        # Clean markdown characters if they slip in
        response_content = response_content.strip()
        if response_content.startswith("```json"):
            response_content = response_content[7:]
        if response_content.endswith("```"):
            response_content = response_content[:-3]
        response_content = response_content.strip()
        
        evaluation = json.loads(response_content)
        
        # Post-process detailed feedback to enforce hard score rules (e.g. Skipped or Gibberish)
        detailed = evaluation.get("detailed_feedback", [])
        gibberish_keywords = {"xyz", "abc", "asdf", "test", "qwerty", "none", "no"}
        
        for item in detailed:
            ans = str(item.get("answer", "")).strip().lower()
            if ans == "skipped" or ans in gibberish_keywords or len(ans) <= 3:
                # Force zero for skipped or obvious gibberish
                if ans == "skipped" or ans in gibberish_keywords:
                    item["technical_score"] = 0.0
                    item["soft_skills_score"] = 0.0
                    if ans == "skipped":
                        item["feedback"] = "Question was skipped by the candidate."
                elif len(ans.split()) <= 2:
                    item["technical_score"] = min(float(item.get("technical_score") or 0.0), 30.0)
                    item["soft_skills_score"] = min(float(item.get("soft_skills_score") or 0.0), 20.0)

        # Calculate overall averages
        if detailed:
            tech_scores = [float(q.get("technical_score") or 0.0) for q in detailed]
            soft_scores = [float(q.get("soft_skills_score") or 0.0) for q in detailed]
            
            avg_tech = sum(tech_scores) / len(detailed)
            avg_soft = sum(soft_scores) / len(detailed)
            avg_final = (avg_tech + avg_soft) / 2.0
            
            evaluation["technical_score"] = round(avg_tech, 2)
            evaluation["soft_skills_score"] = round(avg_soft, 2)
            evaluation["final_score"] = round(avg_final, 2)
        else:
            evaluation["technical_score"] = 0.0
            evaluation["soft_skills_score"] = 0.0
            evaluation["final_score"] = 0.0
            
        return evaluation

    except Exception as e:
        print(f"Error evaluating candidate transcript: {str(e)}")
        # Construct fallback scorecard
        return {
            "technical_score": 0.0,
            "soft_skills_score": 0.0,
            "final_score": 0.0,
            "detailed_feedback": [
                {
                    "question_number": i + 1,
                    "question": qa.get("question", ""),
                    "answer": qa.get("answer", ""),
                    "technical_score": 0.0,
                    "soft_skills_score": 0.0,
                    "feedback": "Evaluation failed due to system/network issues."
                } for i, qa in enumerate(qas_history)
            ],
            "technical_summary": "Failed to generate summary automatically.",
            "soft_skill_summary": "Failed to generate summary automatically.",
            "recommendation": "Manual Transcript Review Required"
        }
