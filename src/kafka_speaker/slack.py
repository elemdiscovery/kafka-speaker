from pathlib import Path
import json
from typing import Dict, List, Callable
import time
import random

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

# List of friendly emojis to assign to users
FRIENDLY_EMOJIS = [
    ':unicorn_face:', ':smiley_cat:', ':pouting_cat:', ':penguin:', ':chicken:', ':llama:', ':frog:', 
    ':octopus:', ':tropical_fish:', ':turtle:', ':rabbit:', ':mouse:', ':hamster:', 
    ':snake:', ':horse:', ':sheep:', ':monkey:', ':dog:', ':cat2:', ':bird:', 
    ':koala:', ':fox_face:', ':wolf:', ':rabbit2:', ':mouse2:', ':cow:', ':dragon:', 
    ':crocodile:', ':leopard:', ':tiger:', ':elephant:', ':whale:', ':dolphin:', ':fish:', 
    ':blowfish:', ':duck:', ':eagle:', ':flamingo:', ':hippopotamus:', ':owl:', ':sloth:', ':black_cat:', ':tiger:', ':rage:'
]

class SlackUploader:
    def __init__(self, token: str):
        """Initialize the Slack uploader with a bot token
        
        Args:
            token: Slack bot user OAuth token
        """
        self.client = WebClient(token=token)
        self._user_emojis = {}  # Cache for user -> emoji mappings
        self._available_emojis = FRIENDLY_EMOJIS.copy()  # Available emojis for assignment

    def _assign_emoji(self, username: str) -> str:
        """Consistently assign an emoji to a username"""
        if username not in self._user_emojis:
            # Replenish available emojis if empty
            if not self._available_emojis:
                self._available_emojis = FRIENDLY_EMOJIS.copy()
            # Choose and remove an emoji
            chosen_emoji = random.choice(self._available_emojis)
            self._available_emojis.remove(chosen_emoji)
            self._user_emojis[username] = chosen_emoji
        return self._user_emojis[username]

    def _block_builder(self, text: str, message_files: List[Dict], file_urls: Dict[str, str]) -> Dict:
        """Build a Slack block with text and files
        
        Args:
            text: The message text
            message_files: List of file dictionaries from the message
            file_urls: Mapping of saved_path -> URL from file uploads
            
        Returns:
            Dict containing the Slack blocks structure
        """
        blocks = []
        
        # Add main text block
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": text
            }
        })
        file_links = [
            f"<{file_urls[f['saved_path']]}|{f['filename']}>"
            for f in message_files
            if f['saved_path'] in file_urls
        ]
        # Add divider and file blocks if we have files
        if any(f['saved_path'] in file_urls for f in message_files):
            blocks.append({"type": "divider"})
            
            # Add each file as an image block
            for f in message_files:
                if f['saved_path'] in file_urls:
                    blocks.append({
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"<{file_urls[f['saved_path']]}|{f['filename']}>",
                        }
                    })
        
        return blocks

    def _upload_files(self, files: List[Dict], conversation_dir: Path, channel: str) -> Dict[str, str]:
        """Upload all files at once and return mapping of saved_path -> URL"""
        file_urls = {}
        for file in files:
            if file["saved_path"]:
                file_path = conversation_dir / file["saved_path"]
                if file_path.exists():
                    url = self._upload_file(file_path, channel, file["filename"], file["description"])
                    if url:
                        file_urls[file["saved_path"]] = url
        return file_urls

    def _upload_file(self, file_path: Path, channel: str, original_filename: str, alt_text: str) -> str:
        """Upload a file to Slack and return its share URL
        
        Args:
            file_path: Path to the file to upload
            channel: Channel ID to upload to
            
        Returns:
            The file's share URL
        """
        try:
            response = self.client.files_upload_v2(
                channel=channel,
                file=str(file_path),
                filename=original_filename,
                title=original_filename,
                initial_comment=alt_text
            )
            return response.data["file"]["permalink"]
        except SlackApiError as e:
            print(f"Error uploading file {file_path}: {e.response['error']}")
            return ""

    def upload_conversation(
        self, 
        conversation_data: Dict, 
        channel: str, 
        file_channel: str | None = None,
        conversation_dir: Path | str = '',
        wait_time_fn: Callable[[], int] = lambda: 1,
        thread_messages: bool = True
    ):
        """Upload a conversation and its attachments to Slack
        
        Args:
            conversation_data: Dictionary containing conversation data
            channel: Channel ID to upload to
            file_channel: Channel ID to upload files to
            conversation_dir: Directory containing attachments
            wait_time_fn: Function that returns wait time between messages
            thread_messages: If True, replies are threaded. If False, all messages post to channel
        """
        conversation_folder = Path(conversation_dir)
        
        # First, upload ALL files for ALL conversations
        all_files = []
        for conversation in conversation_data["conversations"]:
            for message in conversation["messages"]:
                all_files.extend(message["files"])
        
        # Upload all files once and get the URLs
        upload_channel = file_channel or channel
        file_urls = self._upload_files(all_files, conversation_folder, upload_channel)
        time.sleep(wait_time_fn() + wait_time_fn() + wait_time_fn())
        
        # Now process each conversation
        for conversation in conversation_data["conversations"]:
            first_message = conversation["messages"][0]
            thread_ts = None
            
            try:
                response = self.client.chat_postMessage(
                    channel=channel,
                    blocks=self._block_builder(first_message["message_content"], first_message["files"], file_urls),
                    username=first_message["sender_name"],
                    icon_emoji=self._assign_emoji(first_message["sender_name"])
                )
                # Only store thread_ts if we want threaded messages
                if thread_messages:
                    thread_ts = response["ts"]
                
                time.sleep(wait_time_fn())
                
            except SlackApiError as e:
                print(f"Error posting message: {e.response['error']}")
                continue
            
            # Send the rest of the messages
            for message in conversation["messages"][1:]:
                try:
                    # Only include thread_ts if threading is enabled
                    kwargs = {
                        "channel": channel,
                        "blocks": self._block_builder(message["message_content"], message["files"], file_urls),
                        "username": message["sender_name"],
                        "icon_emoji": self._assign_emoji(message["sender_name"])
                    }
                    if thread_messages and thread_ts:
                        kwargs["thread_ts"] = thread_ts
                        
                    self.client.chat_postMessage(**kwargs)
                    time.sleep(wait_time_fn())
                    
                except SlackApiError as e:
                    print(f"Error posting message: {e.response['error']}")

def upload_to_slack(
    output_dir: str | Path, 
    channel: str, 
    token: str,
    file_channel: str,
    thread_messages: bool = True,
    wait_time_fn: Callable[[], int] = lambda: random.randint(1, 5)
):
    """Upload processed book content to Slack
    
    Args:
        output_dir: Directory containing conversations.json and attachments
        channel: Channel ID to post to
        token: Slack bot user OAuth token
        file_channel: Channel ID to post files to
    """
    output_dir = Path(output_dir)
    conversations_file = output_dir / "conversations.json"
    attachments_dir = output_dir
    
    if not conversations_file.exists():
        raise FileNotFoundError(f"Conversations file not found: {conversations_file}")
    
    if not attachments_dir.exists():
        raise FileNotFoundError(f"Attachments directory not found: {attachments_dir}")
    
    # Load the conversation data
    with open(conversations_file, 'r', encoding='utf-8') as f:
        conversation_data = json.load(f)
    
    # Upload to Slack
    uploader = SlackUploader(token)
    uploader.upload_conversation(conversation_data, channel, file_channel, attachments_dir, wait_time_fn, thread_messages)