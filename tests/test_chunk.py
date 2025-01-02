import pytest
from kafka_speaker.paragraph import chunk_file, Paragraph

def test_chunk_file_kafka():
    # Get first few paragraphs
    paragraphs = list(chunk_file(
        'pg69327-kafka-der-prozess.txt',
        skip_past='*** START OF THE PROJECT GUTENBERG EBOOK DER PROZESS: ROMAN ***'
    ))
    
    # Test first paragraph (the arrest)
    assert isinstance(paragraphs[0], Paragraph)
    assert paragraphs[0].chapter_title == "ERSTES KAPITEL"
    assert paragraphs[0].chapter_subtitle == "VERHAFTUNG · GESPRÄCH MIT FRAU GRUBACH · DANN FRÄULEIN BÜRSTNER"
    assert paragraphs[0].paragraph_number == 1
    assert paragraphs[0].content.startswith("Jemand mußte Josef K. verleumdet haben")

    # Test third paragraph (the conversation)
    assert isinstance(paragraphs[2], Paragraph)
    assert paragraphs[2].chapter_title == "ERSTES KAPITEL"
    assert paragraphs[2].chapter_subtitle == "VERHAFTUNG · GESPRÄCH MIT FRAU GRUBACH · DANN FRÄULEIN BÜRSTNER"
    assert paragraphs[2].paragraph_number == 3
    assert paragraphs[2].content.startswith('„Wer sind Sie?" fragte K.')