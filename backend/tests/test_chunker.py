"""
Unit tests for Speaker-Aware Transcript Chunker (Gate 3 - Batch 1).

Validates all 14 mandatory test requirements:
- TEST 1: Basic speaker-aware transcript (speakers, content, ordering preserved)
- TEST 2: Speaker role preservation (explicit inline and attendees lookup)
- TEST 3: Timestamp preservation
- TEST 4: Missing speaker ("Unknown Speaker", no crash)
- TEST 5: Missing timestamp (None, no crash)
- TEST 6: Short-turn grouping (prevents micro-chunk fragmentation)
- TEST 7: Long speaker turn (> 300 tokens, sentence boundaries)
- TEST 8: Long-turn overlap (~50-token overlap, no content loss)
- TEST 9: Chunk ordering (chunk_index starts at 0, strictly monotonic)
- TEST 10: Empty transcript (returns [])
- TEST 11: Whitespace-only transcript (returns [])
- TEST 12: Determinism (repeated execution produces identical chunks)
- TEST 13: No external calls (purely offline, no provider or database calls)
- TEST 14: Extremely long sentence fallback (prevents unbounded chunks)
- BONUS: Real-world sample transcript end-to-end verification
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

# Ensure backend directory is in sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.rag.chunker import Chunk, TranscriptChunker, TokenCounter


class TestSpeakerAwareChunker(unittest.TestCase):
    """Test suite for TranscriptChunker."""

    def setUp(self) -> None:
        self.chunker = TranscriptChunker(
            target_chunk_tokens=250,
            max_chunk_tokens=300,
            min_chunk_tokens=50,
            overlap_tokens=50,
        )
        self.token_counter = TokenCounter()

    # ── TEST 1: Basic speaker-aware transcript ─────────────────────────────────

    def test_01_basic_speaker_aware_transcript(self) -> None:
        """Verify multiple speakers, preserved names, content, and ordering."""
        # Provide two substantive speaker turns (each >= 50 tokens)
        turn_alice = (
            "Good morning everyone and welcome to our Q4 product alignment session. "
            "We have three primary objectives to achieve before the upcoming freeze, "
            "including finalizing the design mockups, reviewing customer feedback from "
            "the beta cohort, and establishing cross-functional KPIs across all sub-teams."
        )
        turn_bob = (
            "Thanks Alice. From the engineering side, all backend microservices are currently "
            "operational in staging. We have completed the authentication upgrades and database "
            "migrations, and our focus for this sprint is load testing and resolving edge-case "
            "timeouts before we initiate production rollout."
        )
        transcript = f"[10:00] Alice: {turn_alice}\n\n[10:05] Bob: {turn_bob}\n"

        chunks = self.chunker.chunk(transcript)
        self.assertEqual(len(chunks), 2)

        # Speaker names preserved
        self.assertEqual(chunks[0].speaker_name, "Alice")
        self.assertEqual(chunks[1].speaker_name, "Bob")

        # Content preserved
        self.assertIn("Q4 product alignment session", chunks[0].content)
        self.assertIn("backend microservices", chunks[1].content)
        self.assertIn("load testing", chunks[1].content)

        # Correct ordering
        self.assertEqual(chunks[0].chunk_index, 0)
        self.assertEqual(chunks[1].chunk_index, 1)

    # ── TEST 2: Speaker role preservation ──────────────────────────────────────

    def test_02_speaker_role_preservation(self) -> None:
        """Verify speaker role preserved both from inline tags and attendees header."""
        # 1. Inline role tag
        turn_alice = (
            "We must finalize the dashboard requirements this week to give engineering "
            "sufficient runway for the Q4 launch. The mockups have been reviewed with "
            "the executive team and we are ready to move into active technical scoping."
        )
        turn_bob = (
            "I can implement the required API changes by Friday once the OpenAPI specification "
            "is signed off. The backend repositories are prepared for the contract updates "
            "and database adjustments."
        )
        transcript_inline = (
            f"[00:01:12] Alice (Product Manager): {turn_alice}\n\n"
            f"[00:01:28] Bob (Lead Engineer): {turn_bob}\n"
        )
        chunks = self.chunker.chunk(transcript_inline)
        self.assertEqual(len(chunks), 2)
        self.assertEqual(chunks[0].speaker_role, "Product Manager")
        self.assertIn("Product Manager", chunks[0].content)
        self.assertEqual(chunks[1].speaker_role, "Lead Engineer")
        self.assertIn("Lead Engineer", chunks[1].content)

        # 2. Header-based role tag
        turn_priya = (
            "The relational schema has been optimized for multi-tenant isolation across all organizations. "
            "We added appropriate composite indexes and table partitioning strategies to support performant "
            "querying across high-volume meeting partitions without encountering query timeouts during peak hours."
        )
        turn_dev = (
            "I have updated the architectural decision records and engineering onboarding guides accordingly. "
            "The updated documentation repository now reflects the database schema changes, operational runbooks, "
            "and data retention guidelines for compliance and audit requirements."
        )
        transcript_header = (
            "Meeting Title: Architecture Review\n"
            "Date: October 10, 2026\n"
            "Attendees: Dev (Documentation Lead), Priya (Schema Architect)\n\n"
            f"[11:00] Priya: {turn_priya}\n\n"
            f"[11:05] Dev: {turn_dev}\n"
        )
        chunks_hdr = self.chunker.chunk(transcript_header)
        self.assertEqual(len(chunks_hdr), 2)
        priya_chunk = next(c for c in chunks_hdr if c.speaker_name == "Priya")
        dev_chunk = next(c for c in chunks_hdr if c.speaker_name == "Dev")

        self.assertEqual(priya_chunk.speaker_role, "Schema Architect")
        self.assertIn("Schema Architect", priya_chunk.content)
        self.assertEqual(dev_chunk.speaker_role, "Documentation Lead")
        self.assertIn("Documentation Lead", dev_chunk.content)

    # ── TEST 3: Timestamp preservation ────────────────────────────────────────

    def test_03_timestamp_preservation(self) -> None:
        """Verify timestamps are parsed and preserved in chunk metadata and content."""
        transcript = (
            "[14:35:10] Alice: The automated deployment pipeline completed successfully.\n"
            "[14:40:00] Bob: Metrics look healthy across all cluster nodes.\n"
        )
        chunks = self.chunker.chunk(transcript)
        self.assertGreaterEqual(len(chunks), 1)
        self.assertEqual(chunks[0].timestamp, "14:35:10")
        self.assertIn("14:35:10", chunks[0].content)

    # ── TEST 4: Missing speaker ────────────────────────────────────────────────

    def test_04_missing_speaker(self) -> None:
        """Verify missing speaker metadata safely falls back to 'Unknown Speaker' without crashing."""
        transcript = (
            "System recorded audio fragment without speaker attribution.\n"
            "We discussed the deployment schedule and agreed to deploy Friday evening.\n"
            "The release manager will notify stakeholders prior to maintenance window.\n"
        )
        chunks = self.chunker.chunk(transcript)
        self.assertGreaterEqual(len(chunks), 1)
        self.assertEqual(chunks[0].speaker_name, "Unknown Speaker")
        self.assertIsNone(chunks[0].speaker_role)
        self.assertIsNone(chunks[0].timestamp)
        self.assertIn("Unknown Speaker", chunks[0].content)

    # ── TEST 5: Missing timestamp ──────────────────────────────────────────────

    def test_05_missing_timestamp(self) -> None:
        """Verify missing timestamp results in timestamp=None without crashing."""
        transcript = (
            "Alice (Product Manager): The launch checklist has been prepared.\n"
            "Bob (Engineer): All integration tests are green.\n"
        )
        chunks = self.chunker.chunk(transcript)
        self.assertGreaterEqual(len(chunks), 1)
        self.assertIsNone(chunks[0].timestamp)
        self.assertIn("Alice", chunks[0].speaker_name)
        self.assertIn("Product Manager", chunks[0].speaker_role or "")

    # ── TEST 6: Short-turn grouping ────────────────────────────────────────────

    def test_06_short_turn_grouping(self) -> None:
        """Verify multiple short consecutive turns are grouped into a single chunk."""
        transcript = (
            "[10:00] Alice: Yes.\n"
            "[10:01] Bob: Sounds good.\n"
            "[10:02] Alice: Agreed.\n"
            "[10:03] Bob: See you tomorrow.\n"
        )
        chunks = self.chunker.chunk(transcript)

        # Must not create 4 separate tiny chunks
        self.assertEqual(len(chunks), 1)
        chunk = chunks[0]

        # Both speakers attributed in chunk metadata
        self.assertIn("Alice", chunk.speaker_name)
        self.assertIn("Bob", chunk.speaker_name)

        # All lines preserved with speaker attribution in content
        self.assertIn("[Alice - 10:00]: Yes.", chunk.content)
        self.assertIn("[Bob - 10:01]: Sounds good.", chunk.content)
        self.assertIn("[Alice - 10:02]: Agreed.", chunk.content)
        self.assertIn("[Bob - 10:03]: See you tomorrow.", chunk.content)

    # ── TEST 7: Long speaker turn ──────────────────────────────────────────────

    def test_07_long_speaker_turn(self) -> None:
        """Verify turns exceeding target size are split at sentence boundaries."""
        # Build a monologue exceeding 400 tokens with distinct sentences
        sentences = [
            f"Sentence number {i} provides detailed contextual explanation about the architecture of our distributed system."
            for i in range(1, 30)
        ]
        monologue = " ".join(sentences)
        transcript = f"[09:00] Aryan (Project Manager): {monologue}"

        chunks = self.chunker.chunk(transcript)

        # Multiple chunks must be generated
        self.assertGreater(len(chunks), 1)

        # Speaker metadata preserved across all sub-chunks
        for c in chunks:
            self.assertEqual(c.speaker_name, "Aryan")
            self.assertEqual(c.speaker_role, "Project Manager")
            self.assertEqual(c.timestamp, "09:00")
            # Size within reasonable target bounds
            self.assertLessEqual(c.token_count, self.chunker.max_chunk_tokens + 40)

        # Continuation sub-chunks retain attribution
        self.assertTrue(chunks[1].content.startswith("[Aryan (Project Manager) - 09:00] (cont.):"))

    # ── TEST 8: Long-turn overlap ──────────────────────────────────────────────

    def test_08_long_turn_overlap(self) -> None:
        """Verify adjacent split chunks share approximately 50-token overlap without content loss."""
        sentences = [
            f"Phase {i} focuses on scalable ingestion and robust message serialization across service boundaries."
            for i in range(1, 25)
        ]
        transcript = f"[10:00] Engineer: {' '.join(sentences)}"

        chunks = self.chunker.chunk(transcript)
        self.assertGreaterEqual(len(chunks), 2)

        # Verify overlap between Chunk 0 and Chunk 1
        chunk0_text = chunks[0].content
        chunk1_text = chunks[1].content

        # Extract sentences from Chunk 0 and Chunk 1
        # Overlapping sentence(s) must appear in both chunks
        shared_sentences = [
            s for s in sentences
            if s in chunk0_text and s in chunk1_text
        ]
        self.assertGreater(len(shared_sentences), 0, "Adjacent split chunks must share overlapping sentence(s)")

        # Verify approximate overlap token count
        overlap_text = " ".join(shared_sentences)
        overlap_tokens = self.token_counter.count(overlap_text)
        self.assertGreaterEqual(overlap_tokens, 15)
        self.assertLessEqual(overlap_tokens, 120)

        # Verify no sentence from original text was lost
        all_chunk_text = " ".join(c.content for c in chunks)
        for s in sentences:
            self.assertIn(s, all_chunk_text, f"Sentence was lost during chunking: {s}")

    # ── TEST 9: Chunk ordering ────────────────────────────────────────────────

    def test_09_chunk_ordering(self) -> None:
        """Verify chunk_index starts at 0, increments deterministically, and preserves order."""
        turns = [
            f"[10:{i:02d}] Speaker{i}: Discussion point number {i} covering module specifications."
            for i in range(10)
        ]
        transcript = "\n".join(turns)

        chunks = self.chunker.chunk(transcript)
        self.assertGreater(len(chunks), 0)

        # Indexes start at 0 and are strictly monotonic
        for expected_idx, chunk in enumerate(chunks):
            self.assertEqual(chunk.chunk_index, expected_idx)

    # ── TEST 10: Empty transcript ──────────────────────────────────────────────

    def test_10_empty_transcript(self) -> None:
        """Verify empty transcript input returns an empty list without error."""
        chunks = self.chunker.chunk("")
        self.assertEqual(chunks, [])

    # ── TEST 11: Whitespace-only transcript ────────────────────────────────────

    def test_11_whitespace_only_transcript(self) -> None:
        """Verify whitespace-only transcript input returns an empty list without error."""
        chunks = self.chunker.chunk("   \n\n\t  \r\n   ")
        self.assertEqual(chunks, [])

    # ── TEST 12: Determinism ──────────────────────────────────────────────────

    def test_12_determinism(self) -> None:
        """Verify identical transcript input produces identical chunks across multiple runs."""
        transcript = (
            "Meeting Title: Sprint Retrospective\n"
            "Attendees: Aryan (PM), Sneha (Frontend), Dev (Docs)\n\n"
            "[10:00] Aryan: Let's review what went well in Sprint 1.\n"
            "[10:02] Sneha: The frontend components were delivered ahead of schedule.\n"
            "[10:05] Dev: Documentation is fully aligned with the implementation.\n"
        )

        run1 = self.chunker.chunk(transcript)
        run2 = self.chunker.chunk(transcript)

        self.assertEqual(len(run1), len(run2))
        for c1, c2 in zip(run1, run2):
            self.assertEqual(c1.model_dump(), c2.model_dump())

    # ── TEST 13: No external calls ────────────────────────────────────────────

    def test_13_no_external_calls(self) -> None:
        """Verify chunking operates purely in-memory with zero network or provider calls."""
        transcript = "[10:00] Alice: Purely offline execution test."

        with patch("urllib.request.urlopen") as mock_url, \
             patch("http.client.HTTPConnection") as mock_http:
            chunks = self.chunker.chunk(transcript)

            mock_url.assert_not_called()
            mock_http.assert_not_called()
            self.assertEqual(len(chunks), 1)

    # ── TEST 14: Extremely long sentence fallback ──────────────────────────────

    def test_14_extremely_long_sentence_fallback(self) -> None:
        """Verify an unbounded single sentence without punctuation is safely subdivided."""
        # 800 words without a single punctuation mark
        long_sentence = " ".join(["distributed" for _ in range(800)])
        transcript = f"[12:00] Architect: {long_sentence}"

        chunks = self.chunker.chunk(transcript)

        # Must not produce a single unbounded 800-token chunk
        self.assertGreater(len(chunks), 1)
        for c in chunks:
            # Ensure no unbounded chunk was produced
            self.assertLessEqual(c.token_count, self.chunker.max_chunk_tokens + 40)
            self.assertEqual(c.speaker_name, "Architect")

    # ── BONUS: Real sample transcripts from data/sample_transcripts/ ──────────

    def test_bonus_sample_transcripts_from_repo(self) -> None:
        """Verify chunker processes actual sample transcripts from data/sample_transcripts/."""
        repo_root = Path(__file__).resolve().parent.parent.parent
        samples_dir = repo_root / "data" / "sample_transcripts"

        if not samples_dir.exists():
            self.skipTest("Sample transcripts directory not found")

        for sample_file in samples_dir.glob("*.txt"):
            with open(sample_file, "r", encoding="utf-8") as f:
                content = f.read()

            chunks = self.chunker.chunk(content)
            self.assertGreater(len(chunks), 0, f"Sample {sample_file.name} must yield chunks")

            # Check chunk indexes
            for i, chunk in enumerate(chunks):
                self.assertEqual(chunk.chunk_index, i)
                self.assertIsNotNone(chunk.content)
                self.assertGreater(chunk.token_count, 0)
                self.assertIsNotNone(chunk.speaker_name)


if __name__ == "__main__":
    unittest.main()
