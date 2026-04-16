"""Hashing utilities for deduplication and ID generation."""
import hashlib
import uuid


def hash_job_id(source: str, source_posting_id: str) -> str:
    """Generate a unique job ID from source and posting ID."""
    content = f"{source}:{source_posting_id}"
    return hashlib.sha256(content.encode()).hexdigest()[:16]


def hash_content(content: str) -> str:
    """Generate a hash of content for deduplication."""
    return hashlib.sha256(content.encode()).hexdigest()


def generate_packet_id() -> str:
    """Generate a unique packet ID."""
    return uuid.uuid4().hex[:12]


def generate_run_id() -> str:
    """Generate a unique run ID."""
    return uuid.uuid4().hex[:12]


def generate_request_id() -> str:
    """Generate a unique request ID."""
    return uuid.uuid4().hex[:12]
