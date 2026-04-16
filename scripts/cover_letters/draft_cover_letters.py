#!/usr/bin/env python3
"""
Draft cover letters for packets that need them using OpenAI.

Creates CoverLetterRequest objects to track the request lifecycle.
"""
import argparse
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from utils.fileio import read_json, write_json, read_text, write_text, list_json_files
from utils.timestamps import now_iso, timestamp_for_filename
from utils.hashing import generate_request_id

try:
    from openai import OpenAI
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False


QUEUE_DIR = PROJECT_ROOT / "data" / "queues"
COVER_LETTERS_DIR = PROJECT_ROOT / "artifacts" / "cover_letters"


def load_cover_letter_corpus() -> tuple[str, str]:
    """Load the cover letter corpus file and return content + path."""
    corpus_path = PROJECT_ROOT / "config" / "applicant" / "cover_letters_master.md"
    if corpus_path.exists():
        return read_text(corpus_path), str(corpus_path.relative_to(PROJECT_ROOT))

    example_path = PROJECT_ROOT / "config" / "applicant" / "cover_letters_master.md.example"
    if example_path.exists():
        return read_text(example_path), str(example_path.relative_to(PROJECT_ROOT))

    return "No cover letter corpus available.", "config/applicant/cover_letters_master.md"


def load_prompts() -> tuple[str, str]:
    """Load cover letter prompts."""
    prompts_dir = PROJECT_ROOT / "prompts" / "cover_letter"
    system = read_text(prompts_dir / "system.md")
    user_template = read_text(prompts_dir / "user_template.md")
    return system, user_template


def build_user_prompt(packet: dict, job: dict, corpus: str, template: str) -> str:
    """Build the user prompt for cover letter generation."""
    return template.replace(
        "{{company}}", packet.get("company", "")
    ).replace(
        "{{title}}", packet.get("title", "")
    ).replace(
        "{{location}}", packet.get("location") or "Not specified"
    ).replace(
        "{{description_clean}}", job.get("description_clean") or job.get("description_raw", "")
    ).replace(
        "{{cover_letter_corpus}}", corpus
    )


def create_cover_letter_request(packet: dict, corpus_path: str, reason: str) -> dict:
    """Create a structured cover letter request."""
    return {
        "packet_id": packet["packet_id"],
        "job_id": packet["job_id"],
        "company": packet.get("company", ""),
        "title": packet.get("title", ""),
        "source_url": packet.get("source_url", ""),
        "apply_url": packet.get("apply_url", ""),
        "job_snapshot_path": packet.get("job_snapshot_path", ""),
        "cover_letters_master_path": corpus_path,
        "reason": reason,
        "created_at": now_iso()
    }


def draft_cover_letter(
    packet: dict,
    job: dict,
    corpus: str,
    client: "OpenAI",
    model: str
) -> str:
    """Generate a cover letter draft using OpenAI."""
    system_prompt, user_template = load_prompts()
    user_prompt = build_user_prompt(packet, job, corpus, user_template)

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.7  # Some creativity for cover letters
    )

    return response.choices[0].message.content


def draft_cover_letter_placeholder(packet: dict, job: dict, corpus: str) -> str:
    """Generate a placeholder cover letter when OpenAI is unavailable."""
    return f"""[DRAFT COVER LETTER - REQUIRES REVIEW]

Dear Hiring Manager,

I am writing to express my interest in the {packet.get('title', 'position')} role at {packet.get('company', 'your company')}.

[This is a placeholder draft. Please edit with relevant experience from your background.]

Based on the job requirements, I believe my skills would be a strong match for this role.

Thank you for considering my application.

Sincerely,
[Your Name]

---
Generated: {now_iso()}
Job: {packet.get('company')} - {packet.get('title')}
"""


def get_reason_from_status(cover_letter_status: str) -> str:
    """Map cover letter status to request reason."""
    if cover_letter_status == 'required_discovered_mid_apply':
        return 'discovered_mid_apply'
    return 'predicted_needed'


def process_packets_needing_cover_letters() -> list[Path]:
    """Find all packets that need cover letters drafted."""
    waiting_dir = QUEUE_DIR / "waiting_for_cover_letter_approval"
    packets_dir = PROJECT_ROOT / "data" / "application_packets"

    packets_to_process = []

    # Check waiting queue
    for packet_file in list_json_files(waiting_dir):
        packet = read_json(packet_file)
        if packet.get('cover_letter_status') in ('predicted_needed_draft_pending', 'required_discovered_mid_apply'):
            packets_to_process.append(packet_file)

    # Check packets directory
    for packet_file in list_json_files(packets_dir):
        packet = read_json(packet_file)
        if packet.get('cover_letter_status') in ('predicted_needed_draft_pending', 'required_discovered_mid_apply'):
            packets_to_process.append(packet_file)

    return packets_to_process


def main() -> int:
    parser = argparse.ArgumentParser(description="Draft cover letters for packets")
    parser.add_argument(
        "--packet-id",
        help="Specific packet ID to process"
    )
    parser.add_argument(
        "--local",
        action="store_true",
        help="Use placeholder instead of OpenAI"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be drafted without saving"
    )
    args = parser.parse_args()

    # Set up OpenAI
    client = None
    model = os.environ.get("OPENAI_MODEL", "gpt-4o")

    if not args.local:
        if not HAS_OPENAI:
            print("OpenAI not available, using placeholder")
            args.local = True
        else:
            api_key = os.environ.get("OPENAI_API_KEY")
            if not api_key:
                print("OPENAI_API_KEY not set, using placeholder")
                args.local = True
            else:
                client = OpenAI(api_key=api_key)

    # Load corpus
    corpus, corpus_path = load_cover_letter_corpus()

    # Find packets to process
    if args.packet_id:
        from scripts.queues.transition_packet import find_packet
        packet_path = find_packet(args.packet_id)
        if packet_path is None:
            print(f"Packet not found: {args.packet_id}")
            return 1
        packets_to_process = [packet_path]
    else:
        packets_to_process = process_packets_needing_cover_letters()

    print(f"Found {len(packets_to_process)} packets needing cover letters")

    COVER_LETTERS_DIR.mkdir(parents=True, exist_ok=True)
    drafted_count = 0

    for packet_path in packets_to_process:
        try:
            packet = read_json(packet_path)
            job_path = PROJECT_ROOT / packet.get('job_snapshot_path', '')

            if not job_path.exists():
                print(f"Job snapshot not found for {packet['packet_id']}")
                continue

            job = read_json(job_path)

            print(f"Drafting: {packet['company']} - {packet['title']}")

            # Create request record
            reason = get_reason_from_status(packet.get('cover_letter_status', ''))
            request = create_cover_letter_request(packet, corpus_path, reason)

            if args.local:
                draft = draft_cover_letter_placeholder(packet, job, corpus)
            else:
                draft = draft_cover_letter(packet, job, corpus, client, model)

            if args.dry_run:
                print("Draft preview:")
                print("-" * 40)
                print(draft[:500] + "..." if len(draft) > 500 else draft)
                print("-" * 40)
                continue

            # Save draft
            timestamp = timestamp_for_filename()
            draft_filename = f"{packet['packet_id']}_{timestamp}.md"
            draft_path = COVER_LETTERS_DIR / draft_filename
            write_text(draft_path, draft)

            # Update packet
            packet['cover_letter_path'] = str(draft_path.relative_to(PROJECT_ROOT))
            packet['cover_letter_status'] = 'draft_ready_waiting_approval'
            packet['updated_at'] = now_iso()
            write_json(packet_path, packet)

            # Move to waiting queue if not already there
            waiting_dir = QUEUE_DIR / "waiting_for_cover_letter_approval"
            waiting_dir.mkdir(parents=True, exist_ok=True)

            if packet_path.parent != waiting_dir:
                new_path = waiting_dir / f"{packet['packet_id']}.json"
                write_json(new_path, packet)
                if packet_path.exists():
                    packet_path.unlink()

            drafted_count += 1
            print(f"  Saved: {draft_filename}")

        except Exception as e:
            print(f"Error processing {packet_path}: {e}")

    print(f"\nDrafted {drafted_count} cover letters")
    return 0


if __name__ == "__main__":
    sys.exit(main())
