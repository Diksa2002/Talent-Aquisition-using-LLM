import pdfplumber
import json
import llm_client

def extract_text_from_pdf(pdf_file_path):
    """
    Extracts plain text from a PDF file using pdfplumber.
    """
    text = ""
    try:
        with pdfplumber.open(pdf_file_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
    except Exception as e:
        print(f"Error reading PDF with pdfplumber: {str(e)}")
        raise e
    return text.strip()

def extract_text_from_txt(txt_file_path):
    """
    Extracts plain text from a text file.
    """
    try:
        with open(txt_file_path, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read().strip()
    except Exception as e:
        print(f"Error reading TXT file: {str(e)}")
        raise e

def parse_resume_text_with_llm(resume_text, model_name=None):
    """
    Sends the extracted resume text to Ollama and requests a structured JSON profile back.
    """
    system_prompt = (
        "You are an expert resume parsing assistant. Analyze the provided resume text and extract "
        "the key details in a clean, structured JSON format. You MUST return ONLY a valid JSON object. "
        "Do not include any introductions, explanations, markdown wrapping (such as ```json), or notes. "
        "Conform strictly to the following JSON schema:\n\n"
        "{\n"
        "  \"name\": \"Full Name (string, default to 'Unknown')\",\n"
        "  \"email\": \"Email address (string, default to '')\",\n"
        "  \"phone\": \"Phone number (string, default to '')\",\n"
        "  \"skills\": [\"Skill 1\", \"Skill 2\", ...],\n"
        "  \"projects\": [\"Project 1\", \"Project 2\", ...],\n"
        "  \"education\": [\n"
        "    {\n"
        "      \"degree\": \"Degree title\",\n"
        "      \"institution\": \"University or School name\",\n"
        "      \"year\": 2022\n"
        "    }\n"
        "  ],\n"
        "  \"years_of_experience\": 3.5,\n"
        "  \"current_location\": \"City, State/Country\"\n"
        "}\n\n"
        "If some fields like education year cannot be parsed, set them to null. "
        "Ensure years_of_experience is represented as a float."
    )
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Resume Text:\n{resume_text}"}
    ]
    
    try:
        # Force JSON mode
        response_content = llm_client.query_llm(messages, temperature=0.1, json_mode=True, model_name=model_name)
        
        # Clean response if LLM added markdown formatting
        response_content = response_content.strip()
        if response_content.startswith("```json"):
            response_content = response_content[7:]
        if response_content.endswith("```"):
            response_content = response_content[:-3]
        response_content = response_content.strip()
        
        parsed_json = json.loads(response_content)
        return parsed_json
    except Exception as e:
        print(f"Error parsing resume with LLM: {str(e)}")
        # Fallback to a structured empty response so the app doesn't crash
        return {
            "name": "Unknown Candidate",
            "email": "",
            "phone": "",
            "skills": [],
            "projects": [],
            "education": [],
            "years_of_experience": 0.0,
            "current_location": ""
        }

def process_resume(file_path, file_type, model_name=None):
    """
    Extracts text based on file type and parses it into JSON details.
    Returns (raw_text, parsed_json)
    """
    if file_type.lower() == "pdf":
        raw_text = extract_text_from_pdf(file_path)
    elif file_type.lower() == "txt":
        raw_text = extract_text_from_txt(file_path)
    else:
        raise ValueError(f"Unsupported file type: {file_type}")
        
    parsed_json = parse_resume_text_with_llm(raw_text, model_name=model_name)
    return raw_text, parsed_json
