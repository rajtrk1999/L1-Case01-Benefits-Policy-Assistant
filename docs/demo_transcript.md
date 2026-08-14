# Demo Transcript

This transcript captures a few representative employee questions answered by the benefits policy assistant with retrieved policy context and inline citations.

## Question 1 (Handled Well - Direct / Multi-policy)

**User Question:**
How much does the company match on my 401k and when does it vest?

**Assistant Answer:**
The company matches 100% of the first 3% of your 401(k) contributions and 50% of the next 2%, for a maximum match of 4% [POL-007]. This match vests over three years, with one-third vesting per year [POL-00

**Cited Policy IDs:** POL-007

**Analysis:**
This is a strong example of a direct multi-policy lookup. The assistant retrieved the current 401(k) match and vesting rules and answered using the relevant policy text, including the governing policy citation. It handled the question well because it surfaced the current rule and did not require a guess when multiple matching sections were present.

---

## Question 2 (Handled Well - Direct lookup)

**User Question:**
Can I have both an HSA and a healthcare FSA at the same time?

**Assistant Answer:**
No, you cannot enroll in a Healthcare FSA and an HSA in the same year [POL-006].

**Cited Policy IDs:** POL-006

**Analysis:**
This question exposes a policy-conflict edge case. The assistant includes the sabbatical rules, but the presence of both an eligibility threshold and an approval threshold makes the answer more nuanced. A more robust version would highlight the distinction between eligibility and approval requirements explicitly to avoid ambiguity.

---

## Question 3 (Handled Badly / Policy Conflict)

**User Question:**
How many years of service do I need before I can take a sabbatical?

**Assistant Answer:**
You become eligible for an unpaid four-week sabbatical after five years

**Cited Policy IDs:** No explicit policy citation was returned.

**Analysis:**
This question exposes a policy-conflict edge case. The assistant includes the sabbatical rules, but the presence of both an eligibility threshold and an approval threshold makes the answer more nuanced. A more robust version would highlight the distinction between eligibility and approval requirements explicitly to avoid ambiguity.

---
