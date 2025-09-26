# 🧠 AI Suggestion Engine

An AI service using **Google Gemini API** to generate task suggestions, validate them against predefined rules, and expose APIs through **FastAPI**.

---

## 🚀 Features
- Generate suggestions from context normalized into schema (`AISuggestionResponse`).
- Validate output using both common rules and test case-specific rules.
- Test runner (`test_runner.py`) to run all defined test cases.
- REST API endpoints:
  - `POST /run_test` – Run a single test case.
  - `POST /run_all` – Run all test cases.
- Reason field is enforced to be in **Vietnamese without diacritics**.

---

## 📂 Repository Structure

```
.
├── main.py                 # FastAPI entry point
├── test_runner.py          # Script to run test cases
├── src/
│   ├── llm_client.py       # Calls Gemini API, parses into schema
│   ├── schema.py           # Pydantic schema definition (AISuggestionResponse)
│   ├── rules/
│   │   ├── ai_rules.py     # Validation rules (common + custom)
│   ├── context/            # Input context for each test case (JSON)
│   └── expected/           # Expected output for each test case (JSON)
├── requirements.txt        # Dependencies
└── README.md               # Documentation
```

---

## ⚙️ Installation

### 1. Clone the repository
```bash
git clone https://github.com/KhangNB26/llm_suggestion_engine
cd llm_suggestion_engine
```

### 2. Create virtual environment & install dependencies
```bash
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
.venv\Scripts\activate   # Windows

pip install -r requirements.txt
```

### 3. Configure `.env`
Create a `.env` file in the root folder:

```
GEMINI_API_KEY=your_google_gemini_api_key_here
```

---

## ▶️ Run the Service

### 1. Start the API server
```bash
uvicorn main:app --reload
```

Server runs at: `http://127.0.0.1:8000`

### 2. Swagger UI
Navigate to `http://127.0.0.1:8000/docs` to try out the API.

Endpoints:
- `POST /run_test` – Requires body:  
  ```json
  { "tc": "tc01" }
  ```
- `POST /run_all` – No request body required.

---

## 🧪 Run Tests

### Run all test cases
```bash
python test_runner.py
```

### Example output
- Pass:
  ```
  [tc01] ✅ PASSED (content match)
  ```
- Fail:
  ```
  [tc02] ❌ FAILED content:
     - expected deadline format mismatch
     - confidence out of range
  ```

---

## 📝 Schema

```json
{
  "items": [
    {
      "item_type": 0 or 1,
      "title": "string",
      "parentTaskId": "uuid or null",
      "estimated_minutes": 1-300,
      "deadline": "yyyy-mm-ddTHH:MM:SSZ",
      "confidence": 0.0-1.0,
      "reason": "string (Vietnamese without diacritics)"
    }
  ]
}
```

---

## 🌐 LLM Client (`llm_client.py`)

- Model: `gemini-2.0-flash`
- Config:
  - Forces JSON format response
  - `reason` must always be in Vietnamese without diacritics
- Output validated against `AISuggestionResponse` schema.

---

## 📜 License
MIT – free to use and customize.
