import argparse
import os
import environs
import openai
from kafka_speaker.speaker import process_book
from kafka_speaker.slack import upload_to_slack


def main():
    parser = argparse.ArgumentParser(description='CLI for parsing a Gutenberg book and turning it into a conversation in Slack with file attachments in order to generate sample data.')
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # Sub-parser for the 'parse' command
    parser_parse = subparsers.add_parser('speak', help='Parse a Gutenberg book and turn it into a Slack style conversation with file attachments.')
    # Add arguments specific to the 'parse' command if needed
    parser_parse.add_argument('--file', type=str, help='Path to the document file', default='pg69327-kafka-der-prozess.txt')
    parser_parse.add_argument('--output', type=str, help='Path to the output directory', default=os.getcwd())
    parser_parse.add_argument('--skip-past', type=str, help='Skip through the file until past this line of text', default='*** START OF THE PROJECT GUTENBERG')
    parser_parse.add_argument('--end-at', type=str, help='Stop parsing the file at this line of text', default='*** END OF THE PROJECT GUTENBERG')
    parser_parse.add_argument('--model', type=str, help='OpenAI model to use', default='gpt-4o-mini')
    parser_parse.add_argument('--file-limit', type=int, help='Limit for the number of files to generate. Not a hard cutoff--the speaker will complete the current paragraph.', default=50)

    # Sub-parser for the 'convert' command
    parser_slack = subparsers.add_parser('slack', help='Send parsed data to a Slack channel.')
    parser_slack.add_argument('--input', type=str, help='Input directory containing conversations.json and attachments', default='output')
    parser_slack.add_argument('--channel', type=str, help='Slack channel to send the conversation to. By default, the channel is set in the environment variable SLACK_CHANNEL_ID.', default=None)
    parser_slack.add_argument('--file-channel', type=str, help='Slack channel to send the files to. By default, the channel is set in the environment variable SLACK_FILE_CHANNEL_ID.', default=None)

    args = parser.parse_args()
    env = environs.Env()
    env.read_env()
    if args.command == 'speak':
        client = openai.OpenAI()
        
        # Process the book and get conversation history
        conversation = process_book(
            file_path=args.file,
            skip_past=args.skip_past,
            end_at=args.end_at,
            output_dir=args.output,
            openai_client=client,
            model=args.model,
            file_limit=args.file_limit
        )
        print(f"Successfully processed document. Output saved to {args.output}")

    elif args.command == 'slack':
        token = env("SLACK_BOT_TOKEN")
        channel = args.channel or env("SLACK_CHANNEL_ID")
        file_channel = args.file_channel or env("SLACK_FILE_CHANNEL_ID") or args.channel or env("SLACK_CHANNEL_ID")
        upload_to_slack(args.input, channel, token, file_channel)
    else:
        parser.print_help()

if __name__ == '__main__':
    main()

