import re, json
from retriever import Retriever
from prompts import RAG_PROMPT

ACTION_KEYWORDS = ['block card','block my card','freeze card','dispute','raise dispute','report fraud','cancel card','get balance','balance','transfer']
PII_PATTERNS = [
    (re.compile(r"\b(?:\d[ -]*?){13,19}\b"), '<CARD_MASK>'),
    (re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), '<SSN_MASK>'),
    (re.compile(r"\b\d{10}\b"), '<PHONE_MASK>'),
    (re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"), '<EMAIL_MASK>'),
]

def classify_intent(text):
    t=text.lower()
    for kw in ACTION_KEYWORDS:
        if kw in t:
            return 'action'
    return 'faq'

def redact_pii(text):
    replacements={}
    for pat,mask in PII_PATTERNS:
        def repl(m):
            key = f"{mask}_{len(replacements)+1}"
            replacements[key]=m.group(0)
            return key
        text = pat.sub(repl, text)
    return text, replacements

from openai import OpenAI
import os

client = OpenAI(api_key="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")

def call_llm(prompt: str):
    """
    Calls OpenAI ChatGPT with your RAG prompt and expects a JSON output.
    The AnswerAgent will parse this.
    """
    try:
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {"role": "system", "content": "You are a banking assistant. ALWAYS return JSON with keys: answer, citations."},
                {"role": "user",   "content": prompt}
            ],
            temperature=0.0
        )

        return response.choices[0].message.content

    except Exception as e:
        return json.dumps({"answer": f"LLM error: {str(e)}", "citations": []})


class AnswerAgent:
    def __init__(self):
        self.ret = Retriever()
    def answer(self, redacted_query):
        metas = self.ret.retrieve(redacted_query, top_k=4)
        contexts = '\n\n'.join([f"Source: {m['source']} (chunk {m['chunk_index']})\n{m['text'][:400]}" for m in metas])
        prompt = RAG_PROMPT.format(contexts=contexts, query=redacted_query)
        llm_out = call_llm(prompt)
        try:
            parsed = json.loads(llm_out)
        except:
            parsed = {"answer":"LLM failed to produce JSON","citations":[]}
        return parsed, metas

# ActionAgent
from tools import tool_block_card, tool_raise_dispute, tool_get_balance
class ActionAgent:
    def execute(self, action_name, params):
        if action_name=='block_card':
            return tool_block_card(params['account_id'], params['card_last4'], params.get('reason','user request'))
        if action_name=='raise_dispute':
            return tool_raise_dispute(params['account_id'], params['transaction_id'], params.get('reason','dispute'))
        if action_name=='get_balance':
            return tool_get_balance(params['account_id'])
        return {'error':'unknown action'}
