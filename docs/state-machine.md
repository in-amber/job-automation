# State Machine

## Queue-Based State

**Queue placement IS the state.** Packets do not store a status field. Their location in the queue directories is the authoritative runtime state.

## Queue Locations

Every application packet is in exactly one queue at a time.

```
                                    ┌─────────────┐
                                    │   rejected  │
                                    └─────────────┘
                                          ▲
                                          │ hard reject
                                          │
┌───────────┐     ┌────────────────┐     ┌┴────────────────────┐
│ raw_job   │────▶│ normalized_job │────▶│ application_packets │
└───────────┘     └────────────────┘     └─────────┬───────────┘
                                                   │
                         ┌─────────────────────────┼─────────────────────────┐
                         │                         │                         │
                         ▼                         ▼                         │
          ┌──────────────────────────┐   ┌───────────────┐                  │
          │ waiting_for_cover_letter │   │ ready_to_apply│◀─────────────────┘
          │       _approval          │   └───────┬───────┘
          └──────────────────────────┘           │
                         │                       ▼
                         │              ┌───────────────┐
                         └─────────────▶│  in_progress  │
                         (after approve)└───────┬───────┘
                                                │
                    ┌───────────────────────────┼───────────────────────────┐
                    │                           │                           │
                    ▼                           ▼                           ▼
         ┌──────────────────┐         ┌───────────────┐         ┌───────────────┐
         │ waiting_for_     │         │   completed   │         │    failed     │
         │ signup           │         └───────────────┘         └───────────────┘
         └──────────────────┘
                    │
                    ▼
         ┌──────────────────┐
         │ waiting_for_     │
         │ human_review     │
         └──────────────────┘
```

## Queue Directories

```
data/queues/
├── ready_to_apply/
├── waiting_for_cover_letter_approval/
├── waiting_for_signup/
├── waiting_for_human_review/
├── in_progress/
├── completed/
├── rejected/
└── failed/
```

## Transition Rules

### Packet Building Phase

| From | To | Condition |
|------|------|-----------|
| application_packets/ | waiting_for_cover_letter_approval | Cover letter predicted needed |
| application_packets/ | ready_to_apply | No cover letter needed |

### Cover Letter Flow

| From | To | Condition |
|------|------|-----------|
| waiting_for_cover_letter_approval | ready_to_apply | Cover letter approved |
| in_progress | waiting_for_cover_letter_approval | Cover letter discovered mid-apply |

### Execution Phase

| From | To | Condition |
|------|------|-----------|
| ready_to_apply | in_progress | Worker picks up packet |
| in_progress | completed | Application submitted successfully |
| in_progress | waiting_for_signup | Signup required |
| in_progress | waiting_for_human_review | Manual review required |
| in_progress | failed | Unrecoverable error |

### Recovery

| From | To | Condition |
|------|------|-----------|
| waiting_for_signup | ready_to_apply | Human creates account |
| waiting_for_human_review | completed | Human approves and submits |

## Critical Rule: Non-Blocking Cover Letters

A packet waiting on cover-letter approval MUST NOT block the rest of the queue:
1. Remove it from active application queue
2. Continue processing the next packet
3. Return to it after approval

## Why No Status Field?

Storing status in both the packet JSON and the queue location creates:
- Redundant state that can get out of sync
- Confusion about which is authoritative
- Risk of stale status values

By using queue location as the only state:
- Single source of truth
- No sync issues
- State is always visible from filesystem
