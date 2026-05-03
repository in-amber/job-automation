You are operating under prompts/cowork/master_operator.md and the
apply_to_job_from_packet skill at prompts/cowork/skills/apply_to_job_from_packet/.
Those define your per-packet contract. This prompt only adds the
queue-drain orchestration and write-scope guardrails.

Goal: drain data/queues/ready_to_apply/ by applying to every packet in
it, one at a time.

Loop — repeat until ready_to_apply/ is empty:

1. List data/queues/ready_to_apply/*.json. If empty, stop and print the
   final summary (see below). Otherwise pick the oldest file
   (lexicographic; packet IDs are content-addressed so order is stable).

2. Transition the packet to in_progress:
       scripts/queues/transition_packet.py <packet_id> in_progress
   Read the packet from its new location in data/queues/in_progress/.

3. Apply the packet per SKILL.md (load referenced files, fill fields,
   run the pre-submit audit, submit per submit_policy, escalate per
   escalation_policy.md).

4. Finalize:
   - Write a RunLog to data/run_logs/<run_id>.json
     (schemas/run_log.schema.json).
   - If escalated, also write an InterventionReport to
     data/run_logs/interventions/
     (schemas/intervention_report.schema.json).
   - Transition the packet to its terminal queue via
     scripts/queues/transition_packet.py:
       submitted                → completed
       waiting_for_signup       → waiting_for_signup
       waiting_for_human_review → waiting_for_human_review
       waiting_for_cover_letter → waiting_for_cover_letter_approval
       failed / expired_posting → failed
   - Confirm the source file in in_progress/ is actually gone after the
     transition. If it is not, stop and tell me immediately.

5. Loop back to step 1.

When the queue is drained (or I abort), print a summary table: one row
per packet with packet_id, company, title, result, and confirmation
number if any.

A single failure or escalation must NOT stop the queue. Don't pause to
ask me what to do on an escalation — follow escalation_policy.md, move
the packet to its waiting queue, and continue. Only stop if I say
"abort" or you hit an environment error per the rules below.

Scope of writes — strictly enforced:
- You may only create or modify files under:
    data/queues/
    data/run_logs/
    data/run_logs/interventions/
- You may NOT edit, create, or delete any file under scripts/, schemas/,
  prompts/, config/, tests/, docs/, artifacts/, docker/, or anywhere
  else in the repo. That includes "small fixes," workarounds, or
  patches you think are obviously correct. The codebase is out of
  scope for this run.
- If a script (e.g. transition_packet.py) fails with a permission
  error, sandbox error, FUSE/mount error, or any other environment-
  level issue: STOP the loop, tell me the exact command, the exact
  error message, and the current packet's state, and wait for me to
  fix it. Do not edit the script to work around it. Do not invent a
  tombstone/marker/flag scheme to bypass the failure. Do not retry
  with different code.
- If you believe a script is genuinely buggy (not an environment
  issue), still do not edit it — report it to me and stop.
