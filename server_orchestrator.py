from fastapi import FastAPI
from pydantic import BaseModel
import uuid, requests
from agents import classify_intent, redact_pii, AnswerAgent, ActionAgent

app = FastAPI()
answer_agent = AnswerAgent()
action_agent = ActionAgent()

class ChatRequest(BaseModel):
    session_id: str | None = None
    user_text: str
    account_id: str | None = None
    authenticated: bool = False

@app.post('/chat')
def chat(req: ChatRequest):
    session_id = req.session_id or str(uuid.uuid4())
    intent = classify_intent(req.user_text)
    redacted, replacements = redact_pii(req.user_text)
    print(" User Request Intenet ="+intent)
    if intent=='faq':
        parsed, metas = answer_agent.answer(redacted)
        return {"session_id":session_id, "intent":intent, "response": parsed}
    else:
        # naive action routing for demo
        if 'block' in redacted.lower():
            if not req.authenticated or not req.account_id:
                return {"session_id":session_id, "intent":"action","status":"needs_auth"}
            card_last4 = '4242'
            res = action_agent.execute('block_card', {"account_id":req.account_id, "card_last4":card_last4, "reason":"Customer request"})
            return {"session_id":session_id, "intent":"action","action_result":res}
        if 'balance' in redacted.lower():
            if not req.authenticated or not req.account_id:
                return {"session_id":session_id, "intent":"action","status":"needs_auth"}
            res = action_agent.execute('get_balance', {"account_id":req.account_id})
            return {"session_id":session_id, "intent":"action","action_result":res}
        return {"session_id":session_id, "intent":"unknown"}
