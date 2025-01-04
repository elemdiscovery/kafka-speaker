# Kafka Speaker

This is a toy project for generating sample Slack data.

## Usage

You are sort of on your own if you want to adapt this, but a couple of notes:

- The paragraph titles are sketchy--you'd be better of parsing the HTML files
  from Gutenberg probably to get some more semantic meaning.
- I put a lot of print statements rather than configuring a console logger.
  Sorry. 🙃
- The cost for a couple of full runs (limiting to ~50 files) and dev testing was
  about $5.
- Most of the cost is with DALL-E and the `code_interpreter`.
- The exception handling is very lazy.
- Haven't implemented the Slack upload part yet.
- It would probably be best to manage the threads more tightly. The diversity in
  document generation seems to drop as a thread goes on.
