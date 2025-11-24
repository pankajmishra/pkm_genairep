import requests
FASTAPI_BASE = 'http://127.0.0.1:8001'

def tool_block_card(account_id, card_last4, reason):
    r = requests.post(f"{FASTAPI_BASE}/block_card", json={"account_id":account_id,"card_last4":card_last4,"reason":reason})
    return r.json()

def tool_raise_dispute(account_id, transaction_id, reason):
    r = requests.post(f"{FASTAPI_BASE}/raise_dispute", json={"account_id":account_id,"transaction_id":transaction_id,"reason":reason})
    return r.json()

def tool_get_balance(account_id):
    r = requests.post(f"{FASTAPI_BASE}/get_balance", json={"account_id":account_id})
    return r.json()
