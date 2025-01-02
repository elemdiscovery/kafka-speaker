import argparse
import os

def parse_document(input_file, output_dir, skip_past):
    # Now you can use input_file and output_dir in your function
    print(f"Parsing document from: {input_file}")
    print(f"Output will be saved to: {output_dir}")
    print(f"Skipping past: {skip_past}")
    pass

def convert_to_slack():
    # Function to convert received content into Slack test data
    pass

def main():
    parser = argparse.ArgumentParser(description='CLI for parsing a Gutenberg book and turning it into a conversation in Slack with file attachments in order to generate sample data.')
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # Sub-parser for the 'parse' command
    parser_parse = subparsers.add_parser('parse', help='Parse a Gutenberg book and turn it into a Slack style conversation with file attachments.')
    # Add arguments specific to the 'parse' command if needed
    parser_parse.add_argument('--file', type=str, help='Path to the document file', default='pg69327-kafka-der-prozess.txt')
    parser_parse.add_argument('--output', type=str, help='Path to the output directory', default=os.getcwd())
    parser_parse.add_argument('--skip-past', type=str, help='Skip through the file until past this line of text', default='*** START OF THE PROJECT GUTENBERG')

    # Sub-parser for the 'convert' command
    parser_convert = subparsers.add_parser('speak', help='Send parsed data to a Slack channel.')
    # Add arguments specific to the 'convert' command if needed
    # parser_convert.add_argument('--input', type=str, help='Input data for conversion')

    args = parser.parse_args()

    if args.command == 'parse':
        parse_document(args.file, args.output, args.skip_past)
    elif args.command == 'speak':
        convert_to_slack()
    else:
        parser.print_help()

if __name__ == '__main__':
    main()

