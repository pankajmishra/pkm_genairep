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

ACCOUNTS = {"acct_123":{"balance":1250.75, "cards":[{"last4":"4242","status":"active"}] } }
DISPUTES = {}

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
