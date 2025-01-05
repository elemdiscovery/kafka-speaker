import os
import pytest
from pathlib import Path
import json
from environs import Env
from kafka_speaker.slack import SlackUploader, upload_to_slack
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

@pytest.fixture
def env():
    env = Env()
    env.read_env()
    return env

@pytest.fixture
def slack_token(env):
    return env("SLACK_BOT_TOKEN")

@pytest.fixture
def slack_channel(env):
    return env("SLACK_TEST_CHANNEL_ID")

@pytest.fixture
def slack_file_channel(env):
    return env("SLACK_FILE_CHANNEL_ID")

@pytest.fixture
def test_data_dir():
    return os.path.join(os.path.dirname(__file__), "data", "short_output")

@pytest.fixture
def sample_conversation_data(test_data_dir):
    # Load existing conversation data
    conv_file = os.path.join(test_data_dir, "conversations.json")
    with open(conv_file, 'r') as f:
        return json.load(f)

def test_slack_uploader_initialization(slack_token):
    uploader = SlackUploader(slack_token)
    assert uploader.client is not None


def test_upload_conversation(slack_token, slack_channel, test_data_dir, sample_conversation_data):
    uploader = SlackUploader(slack_token)
    
    # Test uploading the conversation using the test data directory
    uploader.upload_conversation(
        sample_conversation_data,
        slack_channel,
        Path(test_data_dir)
    )
    # If no exception is raised, consider it a success

def test_upload_to_slack_function(slack_token, slack_channel, slack_file_channel, test_data_dir):
    # Test the main upload function with the test data directory
    upload_to_slack(
        test_data_dir,
        slack_channel,
        slack_token,
        slack_file_channel,
        thread_messages=False
    )
    # If no exception is raised, consider it a success
