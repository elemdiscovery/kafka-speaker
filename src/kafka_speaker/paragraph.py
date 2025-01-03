from dataclasses import dataclass, asdict
from typing import List, Iterator
import re

@dataclass
class Paragraph:
    chapter_title: str
    chapter_subtitle: str
    paragraph_number: int
    content: str


def chunk_file(file_path: str, skip_past: str, min_paragraph_length: int = 200) -> Iterator[Paragraph]:
    with open(file_path, 'r', encoding='utf-8') as file:
        lines = file.readlines()

    # Skip to the book title
    start_index = next(i for i, line in enumerate(lines) if skip_past in line)
    start_index += 1
    lines = lines[start_index:]

    # Skip past initial indented metadata and blank lines
    while lines and (not lines[0].strip() or lines[0].startswith(' ' * 4)):
        lines.pop(0)

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
        if re.match(r'^[A-ZÄÖÜ\s·]+$', line) and not any(c.islower() for c in line):
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