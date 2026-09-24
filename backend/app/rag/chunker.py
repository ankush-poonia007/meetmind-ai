"""
Speaker-Aware Transcript Chunker for MeetMind AI RAG Pipeline.

Converts raw meeting transcripts into structured, speaker-aware chunks
suitable for:
1. PostgreSQL transcript_chunks persistence
2. Gemini embedding (gemini-embedding-001)
3. Pinecone vector indexing (meeting_{meeting_id} namespace)
4. Hybrid retrieval (BM25 + Semantic + Reranking)

Locked characteristics:
- Target chunk size: ~200-300 tokens
- Split long turns at sentence boundaries with ~50-token overlap
- Group adjacent short turns to prevent tiny micro-chunks
- Preserve speaker name, role, timestamp, and chronological ordering
- Safe handling of missing metadata (Unknown Speaker, None role, None timestamp)
- Fallback for exceptionally long sentences without punctuation
- Zero external provider or database dependencies
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import tiktoken
from pydantic import BaseModel, Field

from app.core.logging import get_logger

logger = get_logger("rag.chunker")


# ── Output Data Contract ─────────────────────────────────────────────────────

class Chunk(BaseModel):
    """
    RAG-specific chunk contract aligned with PostgreSQL transcript_chunks model.

    Database fields mirrored:
    - chunk_index: int
    - speaker_name: str | None
    - speaker_role: str | None
    - timestamp: str | None
    - content: str
    - chunk_type: str (dialogue, decision, task_mention)
    - involves_user: bool (default False, resolved later by Identity Agent)
    - pinecone_vector_id: str | None (resolved later during Pinecone upsert)
    """

    chunk_index: int = Field(..., description="0-based sequence index")
    speaker_name: str = Field(default="Unknown Speaker", description="Attributed speaker name(s)")
    speaker_role: Optional[str] = Field(default=None, description="Speaker role if known")
    timestamp: Optional[str] = Field(default=None, description="Earliest turn timestamp if known")
    content: str = Field(..., description="Speaker-attributed formatted dialogue content")
    token_count: int = Field(default=0, description="Token count calculated by tiktoken")
    chunk_type: str = Field(default="dialogue", description="Transcript chunk type enum value")
    involves_user: bool = Field(default=False, description="Default False, resolved later by Identity Agent")
    pinecone_vector_id: Optional[str] = Field(default=None, description="Pinecone vector ID, resolved in later batch")


# ── Internal Structures ──────────────────────────────────────────────────────

@dataclass
class SpeakerTurn:
    """Internal intermediate representation of an individual speaker turn."""

    speaker_name: str = "Unknown Speaker"
    speaker_role: Optional[str] = None
    timestamp: Optional[str] = None
    text: str = ""


# ── Token Counter ────────────────────────────────────────────────────────────

class TokenCounter:
    """Deterministic token counter using tiktoken (cl100k_base)."""

    def __init__(self, encoding_name: str = "cl100k_base") -> None:
        try:
            self._encoding = tiktoken.get_encoding(encoding_name)
        except Exception as exc:  # pragma: no cover
            logger.warning("Failed to initialize tiktoken encoding %s: %s", encoding_name, exc)
            self._encoding = None

    def count(self, text: str) -> int:
        """Count tokens in text, falling back to word estimation if encoding unavailable."""
        if not text:
            return 0
        if self._encoding is not None:
            return len(self._encoding.encode(text))
        # Word-based fallback estimation (~1.33 tokens per word)
        return max(1, int(len(text.split()) * 1.33))


# ── Chunker Class ────────────────────────────────────────────────────────────

class TranscriptChunker:
    """
    Deterministic speaker-aware chunker for meeting transcripts.

    Parameters:
    - target_chunk_tokens: Target size for chunks (default: 250 tokens).
    - max_chunk_tokens: Maximum target threshold before splitting (default: 300 tokens).
    - min_chunk_tokens: Threshold below which turns are considered short and eligible
      for grouping (default: 50 tokens).
    - overlap_tokens: Sliding window overlap when splitting long speaker turns
      (default: 50 tokens).
    """

    # Structural header patterns that should be parsed for metadata or stripped as non-spoken noise
    HEADER_REGEX = re.compile(
        r"^(?P<key>Meeting Title|Title|Date|Time|Attendees|Participants|Location|Agenda):\s*(?P<val>.*)$",
        re.IGNORECASE,
    )

    # Turn format 1: [HH:MM] Speaker (Role): Dialogue OR [HH:MM] Speaker: Dialogue
    TURN_REGEX_TIME_FIRST = re.compile(
        r"^\s*\[(?P<time>\d{1,2}:\d{2}(?::\d{2})?(?:\s*[AP]M)?)\]\s*(?P<speaker>[^:\n]+?):\s*(?P<text>.*)$",
        re.IGNORECASE,
    )

    # Turn format 2: Speaker (Role) [HH:MM]: Dialogue OR Speaker [HH:MM]: Dialogue
    TURN_REGEX_SPEAKER_FIRST = re.compile(
        r"^\s*(?P<speaker>[^:\[\n]+?)\s*\[(?P<time>\d{1,2}:\d{2}(?::\d{2})?(?:\s*[AP]M)?)\]:\s*(?P<text>.*)$",
        re.IGNORECASE,
    )

    # Turn format 3: Speaker (Role): Dialogue OR Speaker: Dialogue (no timestamp)
    # Excludes common structural headers to prevent false positives
    TURN_REGEX_NO_TIME = re.compile(
        r"^\s*(?P<speaker>[A-Za-z0-9 _.-]{1,50}(?:\s*\([^)]+\))?):\s*(?P<text>.*)$"
    )

    # Speaker name and role decomposition: "Name (Role)"
    SPEAKER_ROLE_REGEX = re.compile(
        r"^(?P<name>[^(]+?)\s*\((?P<role>[^)]+)\)$"
    )

    # Sentence boundary regex (. ! ? followed by space or newline)
    SENTENCE_SPLIT_REGEX = re.compile(r"(?<=[.!?])\s+")

    def __init__(
        self,
        target_chunk_tokens: int = 250,
        max_chunk_tokens: int = 300,
        min_chunk_tokens: int = 50,
        overlap_tokens: int = 50,
    ) -> None:
        self.target_chunk_tokens = target_chunk_tokens
        self.max_chunk_tokens = max_chunk_tokens
        self.min_chunk_tokens = min_chunk_tokens
        self.overlap_tokens = overlap_tokens
        self.token_counter = TokenCounter()

    # ── Public API ───────────────────────────────────────────────────────────

    def chunk(self, transcript: str) -> List[Chunk]:
        """
        Convert a raw transcript into a list of speaker-aware chunks.

        Handles empty/whitespace transcripts safely by returning an empty list.
        """
        if not transcript or not transcript.strip():
            return []

        # Step 1: Parse metadata headers and raw speaker turns
        attendee_roles, raw_turns = self._parse_transcript(transcript)

        if not raw_turns:
            return []

        # Step 2: Apply attendee role lookup for turns missing explicit inline role
        for turn in raw_turns:
            if not turn.speaker_role and turn.speaker_name in attendee_roles:
                turn.speaker_role = attendee_roles[turn.speaker_name]

        # Step 3: Process turns (split long turns, group adjacent short turns)
        raw_chunks = self._build_chunks(raw_turns)

        # Step 4: Finalize deterministic indexes
        for idx, chunk in enumerate(raw_chunks):
            chunk.chunk_index = idx

        return raw_chunks

    # ── Transcript Parsing ───────────────────────────────────────────────────

    def _parse_transcript(self, transcript: str) -> Tuple[Dict[str, str], List[SpeakerTurn]]:
        """
        Parse raw transcript lines into an attendee role map and ordered speaker turns.

        Strips header noise while extracting attendee role associations where present.
        """
        attendee_roles: Dict[str, str] = {}
        turns: List[SpeakerTurn] = []
        current_turn: Optional[SpeakerTurn] = None

        lines = transcript.splitlines()
        in_header_block = True
        active_header_key: Optional[str] = None
        attendees_raw_text = ""

        for line in lines:
            stripped = line.strip()

            # Empty lines separate paragraphs / turns
            if not stripped:
                active_header_key = None
                continue

            # Check for header lines at start of transcript
            if in_header_block:
                header_match = self.HEADER_REGEX.match(stripped)
                if header_match:
                    active_header_key = header_match.group("key").lower()
                    val = header_match.group("val").strip()
                    if active_header_key in ("attendees", "participants"):
                        attendees_raw_text += " " + val
                    continue
                elif active_header_key in ("attendees", "participants"):
                    # Continuation line of attendees (e.g. multi-line attendee list)
                    # Check if line does not start another key or turn
                    if not self._matches_turn(stripped):
                        attendees_raw_text += " " + stripped
                        continue
                    else:
                        in_header_block = False
                        active_header_key = None
                elif stripped.startswith("---") or stripped.startswith("==="):
                    # Header divider
                    continue
                else:
                    # Non-header line reached
                    in_header_block = False
                    active_header_key = None

            # Process spoken dialogue lines
            turn_match = self._match_turn_line(stripped)
            if turn_match is not None:
                # Flush previous turn if it has content
                if current_turn and current_turn.text.strip():
                    current_turn.text = current_turn.text.strip()
                    turns.append(current_turn)

                speaker_raw = turn_match["speaker"].strip()
                timestamp = turn_match.get("time")
                text = turn_match.get("text", "").strip()

                name, role = self._extract_speaker_name_and_role(speaker_raw)

                current_turn = SpeakerTurn(
                    speaker_name=name,
                    speaker_role=role,
                    timestamp=timestamp,
                    text=text,
                )
            else:
                # Continuation of current turn or initial text without speaker header
                if current_turn is not None:
                    current_turn.text += " " + stripped
                else:
                    # Transcript starts with spoken text without speaker header
                    current_turn = SpeakerTurn(
                        speaker_name="Unknown Speaker",
                        speaker_role=None,
                        timestamp=None,
                        text=stripped,
                    )

        # Flush final turn
        if current_turn and current_turn.text.strip():
            current_turn.text = current_turn.text.strip()
            turns.append(current_turn)

        # Parse attendee roles if accumulated
        if attendees_raw_text.strip():
            attendee_roles.update(self._parse_attendees(attendees_raw_text))

        return attendee_roles, turns

    def _matches_turn(self, line: str) -> bool:
        """Check whether line begins with any recognized speaker turn pattern."""
        return self._match_turn_line(line) is not None

    def _match_turn_line(self, line: str) -> Optional[Dict[str, Optional[str]]]:
        """Try matching line against supported turn formats."""
        # 1. [HH:MM] Speaker: Dialogue
        m1 = self.TURN_REGEX_TIME_FIRST.match(line)
        if m1:
            return {"time": m1.group("time"), "speaker": m1.group("speaker"), "text": m1.group("text")}

        # 2. Speaker [HH:MM]: Dialogue
        m2 = self.TURN_REGEX_SPEAKER_FIRST.match(line)
        if m2:
            return {"time": m2.group("time"), "speaker": m2.group("speaker"), "text": m2.group("text")}

        # 3. Speaker: Dialogue (no timestamp)
        # Avoid matching headers like "Note:", "Agenda:", "Time:", etc.
        m3 = self.TURN_REGEX_NO_TIME.match(line)
        if m3:
            candidate_speaker = m3.group("speaker").strip()
            # Guard against false positives
            lower_candidate = candidate_speaker.lower()
            if lower_candidate in (
                "meeting title", "title", "date", "time", "attendees",
                "participants", "location", "agenda", "note", "summary",
                "action items", "decisions", "discussion",
            ):
                return None
            return {"time": None, "speaker": candidate_speaker, "text": m3.group("text")}

        return None

    def _extract_speaker_name_and_role(self, speaker_str: str) -> Tuple[str, Optional[str]]:
        """Decompose 'Name (Role)' into name and role."""
        if not speaker_str:
            return "Unknown Speaker", None

        match = self.SPEAKER_ROLE_REGEX.match(speaker_str)
        if match:
            name = match.group("name").strip() or "Unknown Speaker"
            role = match.group("role").strip() or None
            return name, role

        return speaker_str.strip() or "Unknown Speaker", None

    def _parse_attendees(self, text: str) -> Dict[str, str]:
        """Parse attendees string e.g. 'Aryan (Project Manager), Sneha (Frontend Developer)'."""
        roles: Dict[str, str] = {}
        # Split by comma or semicolon
        entries = re.split(r"[,;]", text)
        for entry in entries:
            entry = entry.strip()
            if not entry:
                continue
            name, role = self._extract_speaker_name_and_role(entry)
            if name and name != "Unknown Speaker" and role:
                roles[name] = role
        return roles

    # ── Chunk Construction ───────────────────────────────────────────────────

    def _build_chunks(self, turns: List[SpeakerTurn]) -> List[Chunk]:
        """
        Group short turns and split long turns into structured chunks.

        Enforces:
        - Long turns (> max_chunk_tokens) split on sentence boundaries with ~50-token overlap.
        - Short turns (< min_chunk_tokens) grouped adjacent to prevent tiny chunks.
        - Moderate turns (min_chunk_tokens to max_chunk_tokens) kept as cohesive chunks.
        """
        chunks: List[Chunk] = []
        pending_group: List[SpeakerTurn] = []

        def flush_pending_group() -> None:
            if not pending_group:
                return
            chunk = self._create_grouped_chunk(pending_group)
            if chunk is not None:
                chunks.append(chunk)
            pending_group.clear()

        for turn in turns:
            turn_prefix = self._format_turn_prefix(turn)
            turn_full_text = f"{turn_prefix} {turn.text}"
            turn_tokens = self.token_counter.count(turn_full_text)

            # Case A: Long turn exceeding max_chunk_tokens -> split into sub-chunks
            if turn_tokens > self.max_chunk_tokens:
                flush_pending_group()
                long_turn_chunks = self._split_long_turn(turn)
                chunks.extend(long_turn_chunks)
                continue

            # Case B: Standalone turn (between min_chunk_tokens and max_chunk_tokens)
            if turn_tokens >= self.min_chunk_tokens:
                # If we have an accumulated small group, check if adding this turn fits in target
                if pending_group:
                    candidate_tokens = self._calculate_group_tokens(pending_group + [turn])
                    if candidate_tokens <= self.target_chunk_tokens:
                        pending_group.append(turn)
                        flush_pending_group()
                        continue
                    else:
                        flush_pending_group()

                # Emit standalone turn
                chunks.append(self._create_single_turn_chunk(turn))
                continue

            # Case C: Short turn (< min_chunk_tokens)
            # Accumulate into pending group
            candidate_group = pending_group + [turn]
            candidate_tokens = self._calculate_group_tokens(candidate_group)

            if candidate_tokens > self.max_chunk_tokens and pending_group:
                # Flushed existing group before adding new short turn
                flush_pending_group()
                pending_group.append(turn)
            else:
                pending_group.append(turn)
                # If group reached target chunk size, flush it
                if candidate_tokens >= self.target_chunk_tokens:
                    flush_pending_group()

        # Flush any remaining short turns in pending group
        flush_pending_group()

        return chunks

    def _calculate_group_tokens(self, turns: List[SpeakerTurn]) -> int:
        """Calculate total tokens of a list of turns formatted as a group."""
        content = self._format_turns_content(turns)
        return self.token_counter.count(content)

    def _create_single_turn_chunk(self, turn: SpeakerTurn) -> Chunk:
        """Create a Chunk from a single turn."""
        content = self._format_turn_full(turn)
        return Chunk(
            chunk_index=0,
            speaker_name=turn.speaker_name,
            speaker_role=turn.speaker_role,
            timestamp=turn.timestamp,
            content=content,
            token_count=self.token_counter.count(content),
            chunk_type="dialogue",
            involves_user=False,
            pinecone_vector_id=None,
        )

    def _create_grouped_chunk(self, turns: List[SpeakerTurn]) -> Optional[Chunk]:
        """Create a single Chunk from multiple grouped turns."""
        if not turns:
            return None

        content = self._format_turns_content(turns)
        if not content.strip():
            return None

        # Collect unique speaker names and roles preserving order
        unique_speakers = list(dict.fromkeys(t.speaker_name for t in turns if t.speaker_name))
        unique_roles = list(dict.fromkeys(t.speaker_role for t in turns if t.speaker_role))

        speaker_name = ", ".join(unique_speakers) if unique_speakers else "Unknown Speaker"
        speaker_role = ", ".join(unique_roles) if unique_roles else None

        # Earliest timestamp in the grouped turns
        timestamp = next((t.timestamp for t in turns if t.timestamp), None)

        return Chunk(
            chunk_index=0,
            speaker_name=speaker_name,
            speaker_role=speaker_role,
            timestamp=timestamp,
            content=content,
            token_count=self.token_counter.count(content),
            chunk_type="dialogue",
            involves_user=False,
            pinecone_vector_id=None,
        )

    # ── Long Turn Splitting with Overlap ──────────────────────────────────────

    def _split_long_turn(self, turn: SpeakerTurn) -> List[Chunk]:
        """
        Split a long speaker turn into sub-chunks of ~200-300 tokens
        with approximately 50 tokens of overlap on sentence boundaries.
        """
        # 1. Break turn into sentences (with fallback for exceptionally long sentences)
        raw_sentences = self._split_into_sentences(turn.text)
        sentences: List[str] = []

        for s in raw_sentences:
            s_tokens = self.token_counter.count(s)
            if s_tokens > self.max_chunk_tokens:
                # Sentence fallback: split long sentence into word slices
                fallback_slices = self._split_long_sentence(
                    s,
                    target_tokens=self.target_chunk_tokens - 40,
                    overlap_tokens=self.overlap_tokens,
                )
                sentences.extend(fallback_slices)
            else:
                sentences.append(s)

        if not sentences:
            return []

        # Precompute token counts for each sentence to avoid repeated quadratic tokenization
        sent_tokens = [self.token_counter.count(s) for s in sentences]

        # 2. Build sub-chunks using sliding window with overlap
        chunks: List[Chunk] = []
        start_idx = 0
        total_sentences = len(sentences)
        is_first_subchunk = True

        while start_idx < total_sentences:
            curr_sentences: List[str] = []
            idx = start_idx

            prefix = self._format_turn_prefix(turn, is_continuation=not is_first_subchunk)
            prefix_tokens = self.token_counter.count(prefix)
            curr_tokens = prefix_tokens

            while idx < total_sentences:
                # Approximate token addition: sentence tokens + 1 (for separating space)
                add_tokens = sent_tokens[idx] + 1

                # Stop if adding this sentence exceeds max_chunk_tokens and we already have content
                if (curr_tokens + add_tokens > self.max_chunk_tokens) and curr_sentences:
                    break

                curr_sentences.append(sentences[idx])
                curr_tokens += add_tokens
                idx += 1

                # If reached target_chunk_tokens, we can comfortably stop at this sentence boundary
                if curr_tokens >= self.target_chunk_tokens:
                    break

            content = f"{prefix} {' '.join(curr_sentences)}"
            actual_token_count = self.token_counter.count(content)
            chunk = Chunk(
                chunk_index=0,
                speaker_name=turn.speaker_name,
                speaker_role=turn.speaker_role,
                timestamp=turn.timestamp,
                content=content,
                token_count=actual_token_count,
                chunk_type="dialogue",
                involves_user=False,
                pinecone_vector_id=None,
            )
            chunks.append(chunk)

            # If all sentences consumed, we are done
            if idx >= total_sentences:
                break

            # Calculate backwards overlap for the next sub-chunk using precomputed sentence tokens
            overlap_sentences: List[str] = []
            overlap_tokens_accum = 0
            back_idx = idx - 1
            while back_idx >= start_idx:
                add_overlap = sent_tokens[back_idx] + 1
                if (overlap_tokens_accum + add_overlap > self.overlap_tokens) and overlap_sentences:
                    break
                overlap_sentences.insert(0, sentences[back_idx])
                overlap_tokens_accum += add_overlap
                back_idx -= 1

            # Next chunk starts at idx minus overlap sentences
            next_start = idx - len(overlap_sentences)
            # Strictly guarantee forward progress to avoid infinite loop
            if next_start <= start_idx:
                next_start = start_idx + 1

            start_idx = next_start
            is_first_subchunk = False

        return chunks

    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text on sentence boundaries (. ! ?) preserving complete sentences."""
        raw = self.SENTENCE_SPLIT_REGEX.split(text.strip())
        sentences = [s.strip() for s in raw if s.strip()]
        return sentences if sentences else [text.strip()]

    def _split_long_sentence(
        self,
        sentence: str,
        target_tokens: int = 200,
        overlap_tokens: int = 50,
    ) -> List[str]:
        """
        Fallback for exceptionally long sentences without punctuation.

        Splits words into ~target_tokens slices with ~overlap_tokens overlap.
        """
        words = sentence.split()
        if not words:
            return []

        slices: List[str] = []
        start_idx = 0
        total_words = len(words)

        while start_idx < total_words:
            curr_words: List[str] = []
            idx = start_idx

            while idx < total_words:
                candidate = curr_words + [words[idx]]
                tokens = self.token_counter.count(" ".join(candidate))
                if tokens > target_tokens and curr_words:
                    break
                curr_words = candidate
                idx += 1

            slices.append(" ".join(curr_words))

            if idx >= total_words:
                break

            # Calculate overlap backwards
            overlap_words: List[str] = []
            back_idx = idx - 1
            while back_idx >= start_idx:
                candidate = [words[back_idx]] + overlap_words
                cand_tokens = self.token_counter.count(" ".join(candidate))
                if cand_tokens > overlap_tokens and overlap_words:
                    break
                overlap_words = candidate
                back_idx -= 1

            next_start = idx - len(overlap_words)
            if next_start <= start_idx:
                next_start = start_idx + 1

            start_idx = next_start

        return slices

    # ── Formatting Helpers ───────────────────────────────────────────────────

    def _format_turn_prefix(self, turn: SpeakerTurn, is_continuation: bool = False) -> str:
        """
        Format the speaker prefix tag:
        - [Name (Role) - HH:MM]: or (cont.):
        - [Name - HH:MM]:
        - [Name (Role)]:
        - [Name]:
        """
        name = turn.speaker_name or "Unknown Speaker"
        role_part = f" ({turn.speaker_role})" if turn.speaker_role else ""
        time_part = f" - {turn.timestamp}" if turn.timestamp else ""
        cont_part = " (cont.)" if is_continuation else ""

        return f"[{name}{role_part}{time_part}]{cont_part}:"

    def _format_turn_full(self, turn: SpeakerTurn, is_continuation: bool = False) -> str:
        """Format a single turn into its attributed content string."""
        prefix = self._format_turn_prefix(turn, is_continuation=is_continuation)
        text = turn.text.strip()
        return f"{prefix} {text}" if text else prefix

    def _format_turns_content(self, turns: List[SpeakerTurn]) -> str:
        """Format multiple turns into newline-separated attributed content."""
        lines = [self._format_turn_full(t) for t in turns if t.text.strip()]
        return "\n".join(lines)
