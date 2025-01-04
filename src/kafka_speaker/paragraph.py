from dataclasses import dataclass, asdict
from typing import List, Iterator
import re
from itertools import takewhile, dropwhile

@dataclass
class Paragraph:
    chapter_title: str
    chapter_subtitle: str
    paragraph_number: int
    content: str

    def __str__(self):
        parts = [self.chapter_title, self.chapter_subtitle, self.content]
        return "\n".join(part for part in parts if part)


def file_paragraphs(file_path: str, skip_past: str, end_at: str, min_paragraph_length: int = 200) -> Iterator[Paragraph]:
    with open(file_path, 'r', encoding='utf-8') as file:
        # Skip until we find the start marker
        lines = dropwhile(lambda line: skip_past not in line, file)
        next(lines)  # Skip the marker line itself
        
        # Take lines until we hit the end marker (if specified)
        if end_at:
            lines = takewhile(lambda line: end_at not in line, lines)
        
        # Convert to list and skip initial metadata
        lines = list(lines)
        lines = dropwhile(lambda line: not line.strip() or line.startswith(' ' * 4), lines)

    chapter_title = ""
    subtitle = ""
    paragraph_number = 0
    paragraph_content = []

    for line in lines:
        line = line.strip()
        
        if not line:
            # On blank line, yield paragraph if we have enough content
            if paragraph_content and len(' '.join(paragraph_content)) >= min_paragraph_length:
                paragraph_number += 1
                yield Paragraph(chapter_title, subtitle, paragraph_number, ' '.join(paragraph_content))
                paragraph_content = []
            continue

        # Check for chapter title (all caps line)
        if line and not any(c.islower() for c in line.strip()):
            # If we have content, yield the previous paragraph first
            if paragraph_content and len(' '.join(paragraph_content)) >= min_paragraph_length:
                paragraph_number += 1
                yield Paragraph(chapter_title, subtitle, paragraph_number, ' '.join(paragraph_content))
                paragraph_content = []
            
            # If we already have a title, this must be the subtitle
            if chapter_title:
                subtitle = line
            else:
                chapter_title = line
                subtitle = ""
            continue

        # Add line to current paragraph
        paragraph_content.append(line)

    # Handle final paragraph
    if paragraph_content and len(' '.join(paragraph_content)) >= min_paragraph_length:
        paragraph_number += 1
        yield Paragraph(chapter_title, subtitle, paragraph_number, ' '.join(paragraph_content))

# # Example usage
# file_path = 'pg69327-kafka-der-prozess.txt'
# paragraphs = list(chunk_file(file_path))

# for paragraph in paragraphs:
#     print(f"Chapter: {paragraph.chapter_title}, Paragraph {paragraph.paragraph_number}: {paragraph.content[:60]}...")