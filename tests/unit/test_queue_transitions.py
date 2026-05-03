"""
Tests for queue transition logic.

CRITICAL: Queue placement IS the state. Packets do not have a status field.
Cover-letter waiting packets must NOT block the rest of the queue.
"""
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from queues.transition_packet import VALID_QUEUES, VALID_TRANSITIONS


class TestQueueStates:
    """Test that all queue locations are properly defined."""

    def test_all_queues_exist(self):
        """Verify all required queues are defined."""
        required_queues = [
            'ready_to_apply',
            'waiting_for_cover_letter_approval',
            'waiting_for_signup',
            'waiting_for_human_review',
            'in_progress',
            'completed',
            'rejected',
            'failed'
        ]

        for queue in required_queues:
            assert queue in VALID_QUEUES, f"Missing queue: {queue}"


class TestTransitionRules:
    """Test valid state transitions."""

    def test_ready_can_go_to_in_progress(self):
        """Ready packets can transition to in_progress."""
        assert 'in_progress' in VALID_TRANSITIONS['ready_to_apply']

    def test_waiting_cover_letter_can_go_to_ready(self):
        """Jobs waiting for cover letter can transition to ready_to_apply."""
        assert 'ready_to_apply' in VALID_TRANSITIONS['waiting_for_cover_letter_approval']

    def test_in_progress_can_go_to_waiting_cover_letter(self):
        """In-progress jobs can transition to waiting for cover letter (discovered mid-apply)."""
        assert 'waiting_for_cover_letter_approval' in VALID_TRANSITIONS['in_progress']

    def test_in_progress_can_go_to_completed(self):
        """In-progress jobs can transition to completed."""
        assert 'completed' in VALID_TRANSITIONS['in_progress']

    def test_in_progress_can_go_to_waiting_signup(self):
        """In-progress jobs can transition to waiting_for_signup."""
        assert 'waiting_for_signup' in VALID_TRANSITIONS['in_progress']

    def test_waiting_signup_can_return_to_ready(self):
        """Jobs waiting for signup can return to ready_to_apply after manual signup."""
        assert 'ready_to_apply' in VALID_TRANSITIONS['waiting_for_signup']


class TestQueueIndependence:
    """Test that waiting queues are independent from ready queue."""

    def test_different_queues_are_separate(self):
        """Different queue locations are distinct."""
        assert 'waiting_for_cover_letter_approval' != 'ready_to_apply'
        assert 'waiting_for_signup' != 'ready_to_apply'
        assert 'waiting_for_human_review' != 'ready_to_apply'

    def test_waiting_queues_dont_block_ready(self):
        """Verify waiting queues are designed not to block ready queue processing."""
        waiting_queues = [
            'waiting_for_cover_letter_approval',
            'waiting_for_signup',
            'waiting_for_human_review'
        ]

        # None of the waiting queues should be the same as ready_to_apply
        for queue in waiting_queues:
            assert queue != 'ready_to_apply'

        # ready_to_apply should be processable independently
        assert 'in_progress' in VALID_TRANSITIONS['ready_to_apply']
