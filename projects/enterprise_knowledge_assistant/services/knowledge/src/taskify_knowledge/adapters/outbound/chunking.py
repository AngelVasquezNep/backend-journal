"""LangChain token-aware recursive splitting stays inside each source page/section block."""

from dataclasses import replace

import tiktoken
from langchain_text_splitters import RecursiveCharacterTextSplitter

from taskify_knowledge.application.ports.extraction import ChunkText
from taskify_knowledge.domain.block import ExtractedBlock
from taskify_knowledge.domain.locators import PdfLocator, TextLocator


class TokenChunker:
    """Use cl100k_base, at most 800 tokens and a 100-token overlap where splitting permits it."""

    def __init__(self) -> None:
        """Load the cached tokenizer and configure the selected immutable recursive splitter."""
        self.encoding = tiktoken.get_encoding("cl100k_base")
        self.splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
            encoding_name="cl100k_base",
            chunk_size=800,
            chunk_overlap=100,
            disallowed_special=(),
        )

    def split(self, blocks: tuple[ExtractedBlock, ...]) -> tuple[ChunkText, ...]:
        """Split each block independently and retain exact normalized page/line/table/image provenance."""
        result: list[ChunkText] = []
        for block in blocks:
            previous_start, previous_end = -1, 0
            for content in self.splitter.split_text(block.normalized_text):
                if not content.strip():
                    continue
                count = len(self.encoding.encode(content, disallowed_special=()))
                # LangChain's add_start_index subtracts a token overlap from character offsets.
                # Locate exact text with a monotonic, token-measured overlap instead.
                start = block.normalized_text.find(content, previous_start + 1)
                while start >= 0 and previous_start >= 0:
                    overlap = block.normalized_text[start:previous_end]
                    if (
                        start + len(content) > previous_end
                        and len(self.encoding.encode(overlap, disallowed_special=())) <= 100
                    ):
                        break
                    start = block.normalized_text.find(content, start + 1)
                if start < 0 or not 1 <= count <= 800:
                    raise ValueError("Chunking configuration produced an invalid source fragment.")
                previous_start, previous_end = start, start + len(content)
                locator = block.locator
                if isinstance(locator, PdfLocator):
                    locator = replace(locator, text_start=start, text_end=start + len(content))
                elif isinstance(locator, TextLocator):
                    first = locator.line_start + block.normalized_text[:start].count("\n")
                    locator = TextLocator(first, first + content.count("\n"))
                result.append(ChunkText(block, len(result), content, count, locator))
        return tuple(result)
