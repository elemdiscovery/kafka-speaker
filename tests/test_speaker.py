import os
import pytest
from environs import Env
import openai
import shutil

from kafka_speaker.paragraph import Paragraph
from kafka_speaker.speaker import KafkaSpeaker, File, process_book

@pytest.fixture
def openai_client():
    env = Env()
    env.read_env()
    
    return openai.OpenAI(
        api_key=env("OPENAI_API_KEY"),
        organization=env("OPENAI_ORGANIZATION"),
        project=env("OPENAI_PROJECT"),
    )

@pytest.fixture
def test_output_dir():
    output_dir = os.path.join(os.path.dirname(__file__), "output")
    # Remove directory and all contents if it exists
    shutil.rmtree(output_dir, ignore_errors=True)
    # Create fresh directory
    os.makedirs(output_dir)
    return output_dir

@pytest.fixture
def output_path(test_output_dir):
    def _output_path(filename):
        return os.path.join(test_output_dir, filename)
    return _output_path

def test_kafka_speaker_initialization(openai_client):
    speaker = KafkaSpeaker(openai_client)
    assert speaker._get_message_assistant is not None
    assert speaker._get_attachment_assistant is not None
    assert speaker._get_message_thread is not None


def test_kafka_speaker_send_paragraph(openai_client):
    speaker = KafkaSpeaker(openai_client)
    paragraph = Paragraph(chapter_title="The Test",
                          chapter_subtitle="An Empty Room",
                          paragraph_number=1,
                          content='''
                          "Could you explain to me how you got here?"

                          I waited nervously by the train and looked back over my shoulder towards the woman speaking.

                          "Sorry? Oh I walked down the hill."

                          "I think you know that's not why I'm asking."

                          And then I jumped.
                          ''')
    responses = speaker.generate_messages(paragraph)
    assert len(responses) > 0
    # Check that at least one message contains an emoji (any non-ASCII character)
    has_emoji = any(
        any(ord(char) > 127 for char in message.message_content)
        for message in responses
    )
    assert has_emoji, "Expected at least one message to contain an emoji/non-ASCII character"

    

def test_kafka_attachment_assistant(openai_client, output_path):
    speaker = KafkaSpeaker(openai_client)
    assert speaker._get_attachment_assistant is not None
    assert speaker._get_attachment_thread is not None

    attachment = File(filename="jump_analysis.txt",
                            docext=".txt",
                            description="A deep dive into the psychological implications of sudden decisions such as jumping in critical moments, including a breakdown of possible existential crises.")

    file_id = speaker._generate_attachment(attachment)
    assert file_id is not None

    file_content = speaker._download_attachment(file_id)
    assert file_content is not None
    # For text files, content should be returned as bytes that can be decoded as UTF-8

    with open(output_path("attachment.txt"), "wb") as f:
        f.write(file_content)
    try:
        file_content.decode('utf-8')
    except (UnicodeDecodeError, AttributeError):
        assert False, "Expected file content to be decodable as UTF-8 text"

        

def test_kafka_png_attachment(openai_client, output_path):
    speaker = KafkaSpeaker(openai_client)
    assert speaker._get_attachment_assistant is not None
    assert speaker._get_attachment_thread is not None

    attachment = File(filename="scene_visualization.png",
                     docext=".png",
                     description="A visual representation of the scene at the train station, showing the protagonist's perspective before being startled by a strange woman.")

    image_content = speaker._generate_image_attachment(attachment)
    assert image_content is not None
    
    # Save the file for inspection
    with open(output_path("attachment.png"), "wb") as f:
        f.write(image_content)
    
    # Check PNG magic bytes
    png_magic_bytes = b'\x89PNG\r\n\x1a\n'
    assert image_content.startswith(png_magic_bytes), "File does not have valid PNG magic bytes"

def test_process_book(openai_client, test_output_dir):
    test_file = os.path.join(os.path.dirname(__file__), "data", "pg30570-kafka-grosser-larm.txt")
    
    # Process the book and get responses
    output = process_book(test_file, skip_past="*** START OF THE PROJECT GUTENBERG EBOOK", end_at="*** END OF THE PROJECT GUTENBERG EBOOK", output_dir=test_output_dir, openai_client=openai_client, model="gpt-4o-mini", file_limit=50)

    conversations = output["conversations"]
    # Basic validation of responses
    assert conversations is not None
    assert len(conversations) > 0
    
    # Get first conversation's messages for testing
    first_conversation = conversations[0]
    assert 'messages' in first_conversation
    messages = first_conversation['messages']
    
    # Check that we have both messages and attachments in the messages
    message_responses = [m for m in messages if m['message_content']]
    attachment_responses = [m for m in messages if m['files']]
    
    assert len(message_responses) > 0, "Expected at least one message response"
    assert len(attachment_responses) > 0, "Expected at least one attachment response"
    
    # Verify that messages contain emojis (non-ASCII characters)
    has_emoji = any(
        any(ord(char) > 127 for char in msg['message_content'])
        for msg in message_responses
    )
    assert has_emoji, "Expected at least one message to contain an emoji/non-ASCII character"

    # Check that the output file exists
    output_file = os.path.join(test_output_dir, "conversations.json")
    assert os.path.exists(output_file), "Expected output file to exist"

    # Check that there's an attachment saved
    attachment_file = attachment_responses[0]['files'][0]['saved_path']
    assert os.path.exists(attachment_file), "Expected attachment file to exist"







