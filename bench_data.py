"""
Fixed inputs for the benchmark. Everything here is synthetic and written for
this repository (CC0), so anyone can rerun the exact same requests.

A "state" is one support ticket, optionally padded with that customer's prior
messages and order records. Padding is how the benchmark varies state size
(roughly 30, 440 and 1,800 input tokens, plus a one-word control) while keeping the question set and
the decision identical — the only thing fan-out changes is how often the state
is paid for.
"""

from __future__ import annotations

import random

TICKETS: list[dict[str, str]] = [
    {"id": "t01", "text": "I was charged twice for my March invoice. Please refund the duplicate charge today, my card is close to its limit."},
    {"id": "t02", "text": "The export to CSV button has been spinning forever since yesterday's update. We need the report for a board meeting on Friday."},
    {"id": "t03", "text": "Can I upgrade from the Team plan to Business mid-cycle, and will I be billed pro rata? Also do you offer annual discounts?"},
    {"id": "t04", "text": "Your API returns 500 errors for about one request in ten since this morning. Our checkout depends on it. This is costing us sales right now."},
    {"id": "t05", "text": "Honestly thinking of moving to a competitor. They offer SSO on the cheaper plan and your support took four days to reply last time."},
    {"id": "t06", "text": "Just wanted to say the new dashboard is great, thanks. Small thing: the dark mode toggle does not remember my choice."},
    {"id": "t07", "text": "I cancelled my subscription last month but I was still charged on the 3rd. I want that money back and confirmation it will not happen again."},
    {"id": "t08", "text": "How do I add a second admin to our workspace? The settings page only shows the owner and I cannot find an invite option."},
]

HISTORY: list[str] = [
    "Customer: Hi, I have a question about my account settings and notifications.",
    "Agent: Thanks for reaching out. Could you share the workspace name so I can look it up?",
    "Customer: Sure, it is the one registered under our finance team email address.",
    "Agent: Found it. I can see two active seats and one pending invitation from last week.",
    "Customer: The pending one was for a contractor who has since left, you can remove it.",
    "Agent: Done, the invitation is revoked. Anything else I can help with today?",
    "Customer: Our monthly usage report arrived late again this month, around the 9th.",
    "Agent: Reports are generated on the 1st but delivery can queue behind large accounts.",
    "Customer: Could you send it to a shared mailbox instead of my personal address?",
    "Agent: Yes, I have added the shared mailbox as a report recipient from next month.",
    "Customer: We are also evaluating the audit log feature for a compliance review.",
    "Agent: Audit logs are available on the Business plan and retain 400 days of events.",
    "Customer: Is there a way to export them automatically to our storage bucket?",
    "Agent: There is a scheduled export in the integrations tab; it runs every six hours.",
    "Customer: Great. Last thing, our invoices should show our VAT number going forward.",
    "Agent: I have added the VAT number to the billing profile; it applies to new invoices.",
]

ORDER_FIELDS = ["order_id", "date", "plan", "seats", "amount_usd", "status"]
PLANS = ["Starter", "Team", "Business"]
STATUSES = ["paid", "paid", "paid", "refunded", "failed"]

# Target sizes, by how much context rides along with the ticket.
SIZES: dict[str, dict[str, int]] = {
    # "tiny" is a control, not a workload: a one-word state, so its implied
    # per-request cost is almost entirely fixed overhead. Regressing the other
    # sizes against it separates overhead from the state itself.
    "tiny": {"history": 0, "orders": 0},
    "small": {"history": 0, "orders": 0},
    "medium": {"history": 10, "orders": 6},
    "large": {"history": 40, "orders": 30},
}


def build_state(ticket: dict[str, str], size: str, seed: int = 7) -> dict | str:
    """The ticket alone, or the ticket plus deterministic account context."""
    spec = SIZES[size]
    if size == "tiny":
        return "Ticket."
    if spec["history"] == 0 and spec["orders"] == 0:
        return ticket["text"]
    rng = random.Random(f"{seed}:{ticket['id']}:{size}")
    history = [HISTORY[i % len(HISTORY)] for i in range(spec["history"])]
    orders = [
        {
            "order_id": f"ORD-{rng.randint(10000, 99999)}",
            "date": f"2026-{rng.randint(1, 9):02d}-{rng.randint(1, 28):02d}",
            "plan": rng.choice(PLANS),
            "seats": rng.randint(1, 40),
            "amount_usd": round(rng.uniform(9, 900), 2),
            "status": rng.choice(STATUSES),
        }
        for _ in range(spec["orders"])
    ]
    return {"new_ticket": ticket["text"], "prior_messages": history, "orders": orders}


# Eight questions of all three types. For each N the set is split into 8/N
# disjoint subsets (see subsets()), so every question appears equally often at
# every N and N is not confounded with which questions were asked.
QUESTIONS: list[tuple[str, dict]] = [
    ("is_billing", {"type": "noul", "instructions": "Is the new ticket about billing, charges or refunds?"}),
    ("department", {
        "type": "choice",
        "instructions": "Which team should handle the new ticket?",
        "criteria": {
            "billing": "Payments, invoices, refunds, plan changes",
            "technical": "Bugs, errors, outages, integrations",
            "account": "Users, permissions, settings",
            "feedback": "Praise or suggestions with no action needed",
        },
    }),
    ("urgency", {
        "type": "score",
        "instructions": "How urgent is the new ticket?",
        "criteria": ["Can wait a week", "Handle this week", "Handle today", "Handle within the hour"],
    }),
    ("wants_refund", {"type": "noul", "instructions": "Does the customer ask for money back?"}),
    ("sentiment", {
        "type": "choice",
        "instructions": "What is the customer's tone in the new ticket?",
        "criteria": {"positive": None, "neutral": None, "frustrated": None, "angry": None},
    }),
    ("churn_risk", {
        "type": "score",
        "instructions": "How likely is this customer to cancel, based on the new ticket?",
        "criteria": ["Unlikely", "Possible", "Likely"],
    }),
    ("mentions_competitor", {"type": "noul", "instructions": "Does the customer mention moving to or comparing with a competitor?"}),
    ("production_impact", {"type": "noul", "instructions": "Is the customer's own production system or revenue affected right now?"}),
]

QUESTION_COUNTS = [2, 4, 8]


def subsets(n: int, seed: int = 11) -> list[list[str]]:
    """8/n disjoint subsets of size n covering all eight questions, from one
    seeded permutation so the grouping is not the authoring order."""
    ids = [q for q, _ in QUESTIONS]
    random.Random(f"{seed}:{n}").shuffle(ids)
    return [ids[i : i + n] for i in range(0, len(ids), n)]
