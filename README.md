# Bank-MCP — Multimodal Bank Customer Chatbot (POC)

This repository is a Proof-of-Concept for a multimodal bank customer chatbot with:
- RAG (PDF ingest -> FAISS)
- RouterAgent (intent classification + PII redaction)
- AnswerAgent (RAG-based answer composer)
- ActionAgent (calls mock banking FastAPI endpoints)
#- n8n webhook logging example
- FastAPI orchestrator to expose `/chat`

## Quickstart (local)
1. Create Conda env (recommended): `conda create -n bankmcpnew python=3.10 -y && conda activate bankmcpnew`
2. Install requirements: `pip install -r requirements.txt`
3. Locate the Bank-project direct: cd /d/development/genai/bank-mcp1
4. Put sample PDFs into `pdfs/` (a couple of example policy PDFs may be included)
5. Ingest PDFs: `python ingest.py` -- This option is now optional. PDF can be injested through UI
6. After initial setup use `conda activate bankmcpnew` to switch to environment
6. Start mock banking API: `uvicorn server_fastapi:app --port 8001 --reload`
7. Start orchestrator: `uvicorn server_orchestrator:app --port 8000 --reload`
8. Test with curl / Postman to POST `/chat` => `http://127.0.0.1:8000/chat`
9. Start the streamlit server `streamlit run app.py`
10. Access Streamlit API through : http://localhost:8501/

# Note: For API Key in agents.py -> Consider reaching owner of repo to run. Or use your own Open API Key to run the project.
## Access doc of FastAPI-with Banking Transaction URL: 
http://127.0.0.1:8001/docs

## Notes
- The included `call_llm` is a placeholder. Replace with OpenAI or your LLM.
- n8n webhook URL is configured in `server_orchestrator.py` as `N8N_WEBHOOK` (replace).

====================================================================================
## Access docs of server_orchestrator API with Request classification : 
#URL: 
http://127.0.0.1:8000/chat
{
  "session_id": "test_id",
  "user_text": "What is account balance?",
  "account_id": "acct_123",
  "authenticated": true
}

#Response: 
{
  "session_id": "test_id",
  "intent": "action",
  "action_result": {
    "status": "ok",
    "balance": 1250.75
  }
}
===================================================================================
Case 1: User says: “Block my card immediately”

System flow:
- Orchestrator receives request
- RouterAgent → intent = "action"
- PII redaction masks any sensitive data
- ActionAgent → tool_block_card()
- tool hits core banking FastAPI mock /block-card
- Response returned
- n8n logs it
- Orchestrator returns JSON to frontend

curl -X 'POST' \
  'http://127.0.0.1:8000/chat' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "session_id": "test_id",
  "user_text": "Block my card immediately?",
  "account_id": "acct_123",
  "authenticated": true
}'
{
  "session_id": "test_id",
  "intent": "action",
  "action_result": {
    "status": "ok",
    "card_last4": "4242"
  }
}
===============================================================================
Case 2: User says: “What is the ATM withdrawal limit?”

System Flow:
- Orchestrator receives request
- RouterAgent → intent = "faq"
- PII redaction
- AnswerAgent → RAG retrieval → top chunks
- Builds RAG prompt
- OpenAI GPT-4o-mini responds in JSON
- Orchestrator returns JSON to frontend

====================================================================================

