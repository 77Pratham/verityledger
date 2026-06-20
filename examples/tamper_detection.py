"""
Demonstrates tamper detection: modify a stored log entry after the fact,
and show that verify() catches it.

Run: python examples/tamper_detection.py
"""

import json

from verityledger import ChainIntegrityError, Tracer

LOG_PATH = "./tamper_demo_log.jsonl"

tracer = Tracer(log_path=LOG_PATH)
with tracer.session(agent="finance-bot") as session:
    session.log_decision("approve refund", reasoning="order was damaged, refund $42.00")
    session.log_decision("notify customer", reasoning="email confirmation sent")

session_id = session.id
print(f"Session: {session_id}")

valid, _ = tracer.verify(session_id)
print(f"Before tampering, chain valid: {valid}")

# Simulate someone editing the log file directly to change a recorded amount
with open(LOG_PATH) as f:
    lines = f.readlines()

tampered = []
for line in lines:
    entry = json.loads(line)
    if entry.get("session_id") == session_id and entry["data"].get("decision") == "approve refund":
        entry["data"]["reasoning"] = "order was damaged, refund $4200.00"
    tampered.append(json.dumps(entry))

with open(LOG_PATH, "w") as f:
    f.write("\n".join(tampered) + "\n")

valid, break_index = tracer.verify(session_id)
print(f"After tampering, chain valid: {valid} (break detected at entry {break_index})")

try:
    tracer.assert_valid(session_id)
except ChainIntegrityError as exc:
    print(f"assert_valid raised: {exc}")
