from typing import Dict
import openai
import json
from dataclasses import asdict, dataclass
from pathlib import Path
import requests
from kafka_speaker.paragraph import Paragraph, file_paragraphs

_message_assistant_name = "Kafka Speaker"
_message_format = {
    "name": "chat_messages",
    "schema": {
        "type": "object",
        "properties": {
            "messages": {
                "type": "array",
                "description": "An array of Slack-style chat messages.",
                "items": {
                    "type": "object",
                    "properties": {
                        "sender_name": {
                            "type": "string",
                            "description": "The name of the person sending the message."
                        },
                        "message_content": {
                            "type": "string",
                            "description": "The content of the chat message."
                        },
                        "files": {
                            "type": "array",
                            "description": "An array of detailed file descriptions associated with the chat message that are pertinent to the conversation. If no files are relevant, return an empty array.",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "filename": {
                                        "type": "string",
                                        "description": "The name of the file being sent in a Slack conversation."
                                    },
                                    "docext": {
                                        "type": "string",
                                        "description": "The document extension of the file."
                                    },
                                    "description": {
                                        "type": "string",
                                        "description": "A detailed description of file contents that emphasizes the kafka-esque nature of the situation that the file is being read in."
                                    }
                                },
                                "required": ["filename", "docext", "description"],
                                "additionalProperties": False
                            }
                        }
                    },
                    "required": ["sender_name", "message_content", "files"],
                    "additionalProperties": False
                }
            }
        },
        "required": ["messages"],
        "additionalProperties": False
    },
    "strict": True
}

_speaker_instructions = '''
You are participating in an art project where we are re-interpreting Kafka texts as Slack channel conversations. The style should be very informal like a text message, but still following the themes and story of the Kafka text.

In particular we want to:

* Use emojis in the messages, but don't just put them at the end of the message, mix them throughout the message.
* Give detailed `description` of the files that the people are sending. You should include at least three paragraphs of decsription of the file contents.
* Please come up with excuses for sending files and referring to them in the conversation. One of the goals is to make the conversation look visually interesting when displayed in Slack, so having additional file attachments will help.
* Some of the attachments should be images, and the others should be office documents (PDFs, Word documents, markdown, etc).

When you receive a paragraph of Kafka-esque text, you should respond with an array of English messages. Try to be whimsical with your grammar and sentence structure, and keep a theme and writing style for the senders in the conversation.

Do not directly use the name "Kafka" in the conversation or file descriptions--we are trying to make Kafka-esque conversations, not refer to Kafka.

Do not use the names of characters when describing the file attachments--describe their situation instead.

Image attachments should be described as .png files. Other types of attachments should be typical office documents, such as PDFs, Word documents, etc. You can also describe markdown and text files.

Do NOT describe audio, video, or archive (zip etc) attachments.
'''

_attachment_assistant_name = "Kafka Attachment"
_attachment_instructions = '''
You are participating in an art project where we are re-interpreting Kafka texts as Slack channel conversations.

Your responsibility is to generate the documents that the people are sending. You'll be given a filename, a document extension, and a description of the document that you need to generate.

Do not directly refer to Kafka in the documents--we are trying to make Kafka-esque documents, not refer to Kafka.

When writing documents, please add whimsical details and lengthen the document to make it more interesting while following the Kafka-esque themes. When you can, embed images in the documents.

For text files, use markdown formatting.

All documents should be in English.

Allowable file types are listed below. If you are asked to generate a file that you can't make or is not listed below, make a markdown file describing the content you would make.
* .txt
* .md
* .pdf
* .docx
* .pptx
* .xlsx
* .csv

Do NOT generate audio, video, or archive (zip etc) attachments.
'''

@dataclass
class File:
    filename: str
    docext: str
    description: str
    saved_name: str | None = None
    saved_path: str | None = None

    def __str__(self):
        # Keep the original string format for the AI
        return f"File: {self.filename}\nDocument Extension: {self.docext}\nDescription: {self.description}"

    def __post_init__(self):
        """Normalize docext after initialization"""
        self.docext = self.docext.lstrip('.')

    @property
    def normalized_docext(self) -> str:
        """Returns the document extension with leading dot"""
        return f'.{self.docext}'

    @property
    def original_name(self) -> str:
        """Returns original filename with extension"""
        return f"{self.filename}{self.normalized_docext}"

    def set_saved_location(self, path: Path | str) -> None:
        """Updates the saved location information"""
        self.saved_path = str(path)
        self.saved_name = path.name

@dataclass
class Message:
    sender_name: str
    message_content: str
    files: list[File]

@dataclass
class Conversation:
    messages: list[Message]
    

class KafkaSpeaker:
    def __init__(self, openai_client: openai.OpenAI, model: str = "gpt-4o-mini"):
        self._client = openai_client
        self._model = model
        self._message_assistant = None
        self._message_thread = None
        self._attachment_assistant = None
        self._attachment_thread = None
    
    @property
    def _get_message_assistant(self):
        if self._message_assistant is None:
            self._message_assistant = self._setup_message_assistant()
        return self._message_assistant

    @property
    def _get_message_thread(self):
        if self._message_thread is None:
            self._message_thread = self._start_thread()
        return self._message_thread
    
    @property
    def _get_attachment_assistant(self):
        if self._attachment_assistant is None:
            self._attachment_assistant = self._setup_attachment_assistant()
        return self._attachment_assistant

    @property
    def _get_attachment_thread(self):
        if self._attachment_thread is None:
            self._attachment_thread = self._start_thread()
        return self._attachment_thread

    def _find_existing_assistant(self, assistant_name: str):
        existing_assistants = self._client.beta.assistants.list(
            order="desc",
            limit="20", # lol paging
        )
        return next(
            (a for a in existing_assistants.data if a.name == assistant_name),
            None
        )

    def _setup_message_assistant(self):
        existing_assistant = self._find_existing_assistant(_message_assistant_name)
        
        assistant_params = {
            "instructions": _speaker_instructions,
            "response_format": { "type": "json_schema", "json_schema": _message_format },
            "model": self._model
        }
        
        if existing_assistant:
            print(f"Assistant {_message_assistant_name} already exists, updating it.")
            _assistant = self._client.beta.assistants.update(
                existing_assistant.id,
                **assistant_params
            )
        else:
            print(f"Assistant {_message_assistant_name} does not exist, creating it.")
            _assistant = self._client.beta.assistants.create(
                name=_message_assistant_name,
                description="An assistant that converts Kafka texts into Slack-style conversations.",
                **assistant_params
            )
        return _assistant
    
    def _start_thread(self, messages: list[dict] = []):
        return self._client.beta.threads.create( messages=messages )

    def _setup_attachment_assistant(self):
        existing_assistant = self._find_existing_assistant(_attachment_assistant_name)
        
        assistant_params = {
            "instructions": _attachment_instructions,
            "tools": [{"type": "code_interpreter"}],
            "model": self._model
        }

        if existing_assistant:
            print(f"Assistant {_attachment_assistant_name} already exists, updating it.")
            _assistant = self._client.beta.assistants.update(
                existing_assistant.id,
                **assistant_params
            )
        else:
            print(f"Assistant {_attachment_assistant_name} does not exist, creating it.")
            _assistant = self._client.beta.assistants.create(
                name=_attachment_assistant_name,
                description="An assistant that generates Kafka-esque documents and images.",
                **assistant_params
            )
        return _assistant

    def _get_assistant_response(self, thread_id: str, assistant_id: str) -> list:
        """
        Common function to get responses from any assistant.
        Returns the list of messages from the assistant.
        """
        run = self._client.beta.threads.runs.create_and_poll(
            thread_id=thread_id,
            assistant_id=assistant_id
        )

        if run.status == "completed":
            return self._client.beta.threads.messages.list(
                thread_id=thread_id,
                run_id=run.id
            )
        else:
            raise Exception(f"Assistant failed to respond: {run.status}")

    def generate_messages(self, paragraph: Paragraph) -> list[Message]:
        message = self._client.beta.threads.messages.create(
            thread_id=self._get_message_thread.id,
            role="user",
            content=str(paragraph)
        )

        new_messages = self._get_assistant_response(
            thread_id=self._get_message_thread.id,
            assistant_id=self._get_message_assistant.id
        )
        
        # Parse the JSON string and extract messages
        parsed_response = json.loads(new_messages.data[0].content[0].text.value)
        responses = [Message(
            sender_name=msg["sender_name"],
            message_content=msg["message_content"],
            files=[File(**file) for file in msg["files"]]
        ) for msg in parsed_response["messages"]]
        return responses

    def _generate_attachment(self, attachment: File) -> str:
        message = self._client.beta.threads.messages.create(
            thread_id=self._get_message_thread.id,
            role="user",
            content=str(attachment)
        )

        new_messages = self._get_assistant_response(
            thread_id=self._get_message_thread.id,
            assistant_id=self._get_attachment_assistant.id
        )

        if (len(new_messages.data[0].attachments) == 0):
            raise Exception("Attachment assistant failed to make an attachment")
        if (len(new_messages.data[0].attachments) > 1):
            print("Attachment assistant returned more than one attachment")
        
        file_id = new_messages.data[0].attachments[0].file_id

        return file_id

    def _download_attachment(self, file_id: str) -> bytes:
        return self._client.files.content(file_id).content
    
    def _generate_image_attachment(self, attachment: File):
        result = self._client.images.generate(
            model="dall-e-3",
            prompt=f"""
            Generate an oil painting in either:
             - a modern expressionistic style
             - an impressionistic style
             - a surreal style
             - a pop art style
             - an abstract style
             
            for a file that was sent in a Slack conversation.

            You are participating in an art project where we are re-interpreting Kafka texts as Slack channel conversations, and your responsibility is to help with the images.

            They should be reflections of office life and the Kafka-esque situations people find themselves in.

            Do not generate images with large amount of text--small amounts are fine when it is appropriate to the scene.

            Attachment:
            {str(attachment)}
            """,
            size="1024x1024",
            style="natural",
            user="elemdiscovery/kafka-speaker"
        )
        response = requests.get(result.data[0].url)
        return response.content
    
    def generate_attachment(self, attachment: File):
        image_extensions = ('png', 'jpg', 'jpeg', 'gif')
        if any(ext in attachment.docext.lower() for ext in image_extensions):
            # Convert the attachment to use .png extension
            attachment.docext = 'png'
            attachment.filename = attachment.filename.rsplit('.', 1)[0]  # Remove any existing extension
            return self._generate_image_attachment(attachment)
        else:
            file_id = self._generate_attachment(attachment)
            return self._download_attachment(file_id)


def process_book(file_path: str, skip_past: str, end_at: str, output_dir: str | Path, openai_client: openai.OpenAI, model: str, file_limit: int) -> Dict:
    """Process a book file and generate Slack-style interpretations
    
    Writes a JSON file containing the conversation history to the output directory

    Args:
        file_path: Path to the book file
        skip_past: String to skip past in the book file
        end_at: String to end at in the book file
        output_dir: Directory to save outputs (string or Path)
        openai_client: OpenAI client instance

    Returns:
        Dict containing the conversation history that was written to the output directory
    """
    # Convert output_dir to Path if it's a string
    output_dir = Path(output_dir)
    
    # Create output directories
    attachments_dir = output_dir / "attachments"
    attachments_dir.mkdir(parents=True, exist_ok=True)
    
    speaker = KafkaSpeaker(openai_client, model)
    conversations: list[Conversation] = []
    file_counter = 0
    
    print(f"Processing file {file_path}")
    
    # Process each paragraph
    for paragraph in file_paragraphs(file_path, skip_past=skip_past, end_at=end_at):
        # Get messages for this paragraph
        print(f"Processing paragraph {paragraph.paragraph_number}")
        messages = speaker.generate_messages(paragraph)
        if file_counter >= file_limit:
            print(f"Reached max files ({file_limit})")
            break
        
        # Create a new conversation for this paragraph
        current_conversation = Conversation(messages=[])
        
        # Process each message and its attachments
        for msg in messages:
            # Handle any file attachments
            for file_desc in msg.files:
                file_counter += 1

                try:
                    file_content = speaker.generate_attachment(file_desc)
                except Exception as e:
                    print(f"Failed to generate attachment.\nFile description: {str(file_desc)}\nError: {e}")
                    continue
                
                # Set up the save path with padded numbering (ATT + 7 digits)
                save_path = attachments_dir / f"ATT{file_counter:07d}{file_desc.normalized_docext}"
                file_desc.set_saved_location(save_path)
                
                # Save the file
                print(f"Saving file to {save_path}")
                with open(save_path, "wb") as f:
                    f.write(file_content)
            
            # Add message to current conversation
            current_conversation.messages.append(msg)
        
        # Add completed conversation to list
        conversations.append(current_conversation)
    
    # Save the conversation data
    output = {
        "conversations": [asdict(conv) for conv in conversations]
    }
    
    with open(output_dir / "conversations.json", "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    return output


