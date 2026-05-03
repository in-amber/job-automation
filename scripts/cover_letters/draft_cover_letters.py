#!/usr/bin/env python3
"""Draft cover letters for packets that need them using OpenAI."""
import argparse
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from utils.fileio import read_json, write_json, read_text, write_text, list_json_files
from utils.timestamps import now_iso, timestamp_for_filename

from openai import OpenAI


QUEUE_DIR = PROJECT_ROOT / "data" / "queues"
COVER_LETTERS_DIR = PROJECT_ROOT / "artifacts" / "cover_letters"

APPLICANT_NAME = "Braden Wilson"
APPLICANT_ADDRESS_LINES = [
    "225 Clifton St, Apt 309",
    "Oakland, CA 94618",
]
APPLICANT_EMAIL = "braden.wilson44@gmail.com"
APPLICANT_PHONE = "617-784-4063"


def _load_env_file() -> None:
    """Best-effort .env loader (avoids python-dotenv dep)."""
    env_path = PROJECT_ROOT / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


def load_cover_letter_corpus() -> str:
    """Load the cover letter corpus file."""
    corpus_path = PROJECT_ROOT / "config" / "applicant" / "cover_letters_master.md"
    if corpus_path.exists():
        return read_text(corpus_path)

    example_path = PROJECT_ROOT / "config" / "applicant" / "cover_letters_master.md.example"
    if example_path.exists():
        return read_text(example_path)

    return "No cover letter corpus available."


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


def build_letter_header() -> str:
    """Build the contact-info header prepended to every cover letter."""
    today = datetime.now().strftime("%-m/%-d/%Y")
    address_block = "  \n".join(APPLICANT_ADDRESS_LINES)
    return (
        f"{APPLICANT_NAME}  \n"
        f"{address_block}  \n"
        f"{APPLICANT_EMAIL} | {APPLICANT_PHONE}  \n"
        f"{today}\n\n"
    )


def slugify_for_filename(text: str, max_len: int = 50) -> str:
    """ATS-safe filename component: ASCII alnum and underscores only."""
    for sep in [" -- ", " – ", " - ", ", ", " ("]:
        if sep in text:
            text = text.split(sep, 1)[0]
            break
    cleaned = re.sub(r"[^A-Za-z0-9]+", "_", text).strip("_")
    return cleaned[:max_len].rstrip("_")


def submission_filename(packet: dict, ext: str) -> str:
    """Build the filename used at upload time."""
    applicant = slugify_for_filename(APPLICANT_NAME)
    company = slugify_for_filename(packet.get("company", "Company"))
    role = slugify_for_filename(packet.get("title", "Role"))
    return f"{applicant}_Cover_Letter_{company}_{role}.{ext}"


def export_docx(md_path: Path, docx_path: Path) -> None:
    """Convert markdown to DOCX via pandoc. Hard-fails on error."""
    if not shutil.which("pandoc"):
        raise RuntimeError(
            "pandoc is not installed. Install it with `brew install pandoc`."
        )
    result = subprocess.run(
        ["pandoc", str(md_path), "-o", str(docx_path)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"pandoc failed (exit {result.returncode}): {result.stderr.strip()}"
        )


def process_packets_needing_cover_letters() -> list[Path]:
    """Find all packets in the cover-letter waiting queue.

    Queue placement is the authoritative signal: anything sitting in
    waiting_for_cover_letter_approval needs a draft. The drafter overwrites
    the deterministic submission DOCX, so re-running on an already-drafted
    packet is safe.
    """
    waiting_dir = QUEUE_DIR / "waiting_for_cover_letter_approval"
    return list(list_json_files(waiting_dir))


def main() -> int:
    parser = argparse.ArgumentParser(description="Draft cover letters for packets")
    parser.add_argument(
        "--packet-id",
        help="Specific packet ID to process"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be drafted without saving"
    )
    args = parser.parse_args()

    _load_env_file()

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("ERROR: OPENAI_API_KEY is not set.", file=sys.stderr)
        return 1
    client = OpenAI(api_key=api_key)
    model = os.environ.get("OPENAI_MODEL", "gpt-4o")

    corpus = load_cover_letter_corpus()

    if args.packet_id:
        from queues.transition_packet import find_packet
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

            body = draft_cover_letter(packet, job, corpus, client, model)
            draft = build_letter_header() + body.lstrip()

            if args.dry_run:
                print("Draft preview:")
                print("-" * 40)
                print(draft[:500] + "..." if len(draft) > 500 else draft)
                print("-" * 40)
                continue

            # Save markdown draft (kept as the LLM's raw output for diagnostics)
            timestamp = timestamp_for_filename()
            draft_filename = f"{packet['packet_id']}_{timestamp}.md"
            draft_path = COVER_LETTERS_DIR / draft_filename
            write_text(draft_path, draft)

            # Export DOCX with submission-ready filename — this is what Cowork uploads
            docx_filename = submission_filename(packet, "docx")
            docx_path = COVER_LETTERS_DIR / docx_filename
            export_docx(draft_path, docx_path)

            packet['cover_letter_path'] = str(docx_path.relative_to(PROJECT_ROOT))
            packet['updated_at'] = now_iso()
            write_json(packet_path, packet)

            from queues.transition_packet import transition_packet
            if not transition_packet(packet['packet_id'], 'ready_to_apply'):
                raise RuntimeError(
                    f"failed to transition {packet['packet_id']} to "
                    f"ready_to_apply after drafting cover letter"
                )

            drafted_count += 1
            print(f"  Saved: {draft_filename}")
            print(f"  Exported: {docx_filename}")

        except Exception as e:
            print(f"Error processing {packet_path}: {e}")

    print(f"\nDrafted {drafted_count} cover letters")
    return 0


if __name__ == "__main__":
    sys.exit(main())
