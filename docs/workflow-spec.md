# Workflow Specification

## n8n Workflows

### 01_ingest_jobs

**Trigger**: Schedule (configurable)

**Steps**:
1. Fetch raw jobs from configured provider
2. Normalize to standard schema
3. Deduplicate against existing jobs
4. Write raw and normalized files locally

**Output**: New normalized jobs in `data/normalized_jobs/`

### 02_screen_jobs

**Trigger**: After ingestion or manual

**Steps**:
1. Load unscreened normalized jobs
2. Call OpenAI with screening prompt + reject rules
3. Parse strict JSON response
4. Write screening decision
5. Route: rejected → `data/queues/rejected/`, apply → next step

**Output**: Screening decisions in `data/screened_jobs/`

### 03_generate_cover_letters

**Trigger**: Packet needs cover letter

**Steps**:
1. Find packets with `cover_letter_status` = `predicted_needed_draft_pending` or `required_discovered_mid_apply`
2. Load job description and cover letter corpus
3. Call OpenAI draft prompt
4. Save draft to `artifacts/cover_letters/`
5. Update packet status to `draft_ready_waiting_approval`
6. Move packet to `waiting_for_cover_letter_approval` queue

**Output**: Draft cover letters awaiting approval

### 04_queue_packets

**Trigger**: Periodic or after screening

**Steps**:
1. Find packets in `screened_apply` state
2. Check cover letter requirements
3. Move eligible packets to `ready_to_apply`
4. Ensure waiting packets don't block queue

**Output**: Packets ready for browser execution

### 05_log_completed_application

**Trigger**: After browser worker completes

**Steps**:
1. Consume run result from Cowork
2. Write run log to `data/run_logs/`
3. Update Google Sheets (applications, runs, interventions)
4. Transition packet to final state

**Output**: Complete audit trail
