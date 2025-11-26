from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uuid

app = FastAPI()

class BlockCardRequest(BaseModel):
    account_id: str
    card_last4: str
    reason: str

class DisputeRequest(BaseModel):
    account_id: str
    transaction_id: str
    reason: str

class BalanceRequest(BaseModel):
    account_id: str

ACCOUNTS = {
    "acct_123": {
        "balance": 1250.75,
        "cards": [{"last4": "4242", "status": "active"}]
    },
    "acct_124": {
        "balance": 3420.10,
        "cards": [{"last4": "1111", "status": "active"}]
    },
    "acct_125": {
        "balance": 875.00,
        "cards": [{"last4": "2222", "status": "blocked"}]
    },
    "acct_126": {
        "balance": 5600.50,
        "cards": [{"last4": "3333", "status": "active"}]
    },
    "acct_127": {
        "balance": 150.25,
        "cards": [{"last4": "4444", "status": "inactive"}]
    },
    "acct_128": {
        "balance": 9999.99,
        "cards": [{"last4": "5555", "status": "active"}]
    }
}

DISPUTES = {
    "disp_001": {"account_id": "acct_124", "reason": "fraudulent transaction", "amount": 200.00},
    "disp_002": {"account_id": "acct_125", "reason": "duplicate charge", "amount": 75.00},
    "disp_003": {"account_id": "acct_126", "reason": "service not rendered", "amount": 560.50},
    "disp_004": {"account_id": "acct_127", "reason": "unauthorized withdrawal", "amount": 100.00},
    "disp_005": {"account_id": "acct_128", "reason": "incorrect billing", "amount": 500.00}
}

@app.post('/block_card')
def block_card(req: BlockCardRequest):
    acct = ACCOUNTS.get(req.account_id)
    if not acct:
        raise HTTPException(404,'Account not found')
    for card in acct['cards']:
        if card['last4']==req.card_last4:
            card['status']='blocked'
            return {"status":"ok","card_last4":req.card_last4}
    raise HTTPException(404,'Card not found')

@app.post('/raise_dispute')
def raise_dispute(req: DisputeRequest):
    dispute_id = str(uuid.uuid4())
    DISPUTES[dispute_id] = {"account_id":req.account_id, "transaction_id":req.transaction_id, "status":"open", "reason":req.reason}
    return {"status":"ok","dispute_id":dispute_id}

@app.post('/get_balance')
def get_balance(req: BalanceRequest):
    acct = ACCOUNTS.get(req.account_id)
    if not acct:
        raise HTTPException(404,'Account not found')
    return {"status":"ok","balance":acct['balance']}
