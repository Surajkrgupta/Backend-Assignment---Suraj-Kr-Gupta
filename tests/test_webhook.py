import os, hmac, hashlib, json
import requests
import time
BASE = "http://localhost:8000"

def compute_sig(secret, body):
    return hmac.new(secret.encode(), body.encode(), hashlib.sha256).hexdigest()

def test_invalid_signature():
    body = '{"message_id":"m1","from":"+919876543210","to":"+14155550100","ts":"2025-01-15T10:00:00Z","text":"Hello"}'
    r = requests.post(BASE + "/webhook", data=body, headers={"Content-Type":"application/json","X-Signature":"bad"})
    assert r.status_code == 401
