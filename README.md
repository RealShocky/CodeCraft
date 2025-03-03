# CodeCraft: AI-Powered Python Project Generator

A powerful tool that turns natural language prompts into complete, well-organized Python projects through custom LLM integration with LM Studio's API. CodeCraft handles everything from code generation to project structure, dependency management, and more.

## Features

- Send prompts to your LM Studio model's API endpoint
- Read prompts from command line or file
- Stream responses in real-time for immediate feedback
- Extract code blocks from responses
- Clean and format code to ensure it's ready for execution
- Copy response or extracted code to clipboard
- Colorized terminal output for better readability
- Detailed error handling and response information
- Intelligent code extraction that reorders functions and blocks logically
- Save extracted code to a file for later use
- **Clean Code Generation**: Extracts clean, executable Python code from the model's response
- **Clipboard Integration**: Automatically copies the cleaned code to the clipboard for easy pasting
- **Code Fixing**: Automatically fixes common issues in generated code, such as:
  - Duplicate class/function definitions
  - Incomplete class implementations
  - Incorrectly restructured TreeNode/BST implementations
  - Duplicate `__init__` methods in classes
- **Auto-saving**: Intelligently saves the generated code to a file with an appropriate name
- **Streaming Support**: Displays the API response in real-time as it's generated
- **Project Folder Organization**: Creates a dedicated project folder for generated files with automatic requirements.txt generation

## Prerequisites

- Python 3.6+
- LM Studio running locally with the API server enabled
- Required Python packages (install with `pip install -r requirements.txt`):
  - requests
  - pyperclip
  - colorama

## Setup

1. Make sure you have Python installed
2. Set up a virtual environment (optional but recommended):
   ```
   python -m venv venv
   .\venv\Scripts\activate  # Windows
   ```
3. Install required packages:
   ```
   pip install -r requirements.txt
   ```
4. Ensure LM Studio is running and serving the API (default: http://localhost:1234)

## Usage

### Basic Usage

```bash
python custom_model.py
```
This will read a prompt from `prompt.txt` and send it to your model.

### Command Line Options

| Option | Short | Description |
|--------|-------|-------------|
| `--prompt` | `-p` | Specify prompt directly |
| `--prompt-file` | `-f` | Read prompt from a file |
| `--temp` | `-t` | Set temperature (default: 0.7) |
| `--streaming` | `-s` | Enable streaming mode |
| `--copy` | `-c` | Copy response to clipboard |
| `--clean` | | Extract and clean code blocks for execution |
| `--fix` | | Fix common code generation issues |
| `--output` | `-o` | Save output to specified file |
| `--auto-save` | | Automatically save code to a file with an appropriate name |
| `--project-folder` | | Create a dedicated project folder for generated files with automatic requirements.txt generation |

### Full Command Reference

```
usage: custom_model.py [-h] [-f FILE] [-u API_URL] [-t TEMPERATURE] [-m MAX_TOKENS] [-s] [-n] [-c] [--clean] [-o OUTPUT] [--auto-save] [--fix] [--project-folder] [prompt]

Interact with LM Studio API

positional arguments:
  prompt                Prompt text (if not provided, reads from file)

optional arguments:
  -h, --help            show this help message and exit
  -f FILE, --file FILE  Path to prompt file (default: prompt.txt)
  -u API_URL, --api-url API_URL
                        LM Studio API URL (default: http://localhost:1234/v1/chat/completions)
  -t TEMPERATURE, --temperature TEMPERATURE
                        Temperature for generation (default: 0.7)
  -m MAX_TOKENS, --max-tokens MAX_TOKENS
                        Maximum tokens to generate (default: 2000)
  -s, --stream          Use streaming API for real-time responses
  -n, --no-copy         Do not copy response to clipboard
  -c, --code-only       Extract and copy only code blocks from response
  --clean               Clean extracted code for execution
  -o OUTPUT, --output OUTPUT
                        Save extracted code to the specified file
  --auto-save           Automatically save code to a file with an inferred name
  --fix                 Attempt to fix common issues in generated code
  --project-folder      Create a dedicated project folder for generated files with automatic requirements.txt generation
```

## Recommended Usage for Code Generation

For the best experience when generating code, we recommend using the following combination of flags:

```bash
python custom_model.py -s -c --clean --fix --auto-save --project-folder "Your prompt here"
```

This will:
1. Show the model response in real-time with streaming (`-s`)
2. Extract only the code blocks from the response (`-c`)
3. Clean and format the code to ensure it's ready for execution (`--clean`)
4. Attempt to fix common issues like duplicate functions (`--fix`)
5. Automatically save the code to a file with an intelligently generated name (`--auto-save`)
6. Create a dedicated project folder for generated files with automatic requirements.txt generation (`--project-folder`)

The code will automatically be copied to your clipboard, allowing you to paste it directly into your editor.

## Examples

1. Get a palindrome check function:
   ```bash
   python custom_model.py -s -c --clean "Write a Python function to check if a string is a palindrome."
   ```

2. Generate a binary search tree implementation:
   ```bash
   python custom_model.py -s -c --clean "Create a Python class for a binary search tree"
   ```

3. Use a custom prompt file with increased temperature:
   ```bash
   python custom_model.py -f prompts/creative_task.txt -t 0.9 -c --clean
   ```

4. Auto-save code with project folder organization:
   ```bash
   python custom_model.py --auto-save --project-folder -p "Create a Flask web app for a to-do list"
   ```

## How the Code Cleaning Works

The `--clean` flag enhances the code extraction process in several ways:

1. **Code Structure Preservation**: Maintains docstrings, comments, and function definitions
2. **Intelligent Block Reordering**: Organizes code blocks in a logical order (classes → functions → other code → main blocks)
3. **Terminal Output Removal**: Filters out interactive prompts and example outputs
4. **Whitespace Normalization**: Ensures consistent indentation and spacing
5. **Pattern Recognition**: Uses heuristics to identify Python code even when not properly formatted in code blocks

This results in clean, executable code that you can paste directly into your editor and run without modifications.

## Automatic Code Fixing

The `--fix` flag adds an additional layer of code processing that attempts to correct common issues in LLM-generated code:

1. **Duplicate Removal**: Eliminates duplicate function and class definitions
2. **Method Consistency**: Handles conflicting method implementations in classes
3. **Code Organization**: Ensures that classes and functions are properly organized

This is particularly helpful for models that sometimes repeat code blocks or generate redundant definitions, ensuring that the final code is clean and ready to run.

## Project Organization

With the `--project-folder` flag, the script creates a complete project structure:
- Creates a dedicated folder with a meaningful name derived from your prompt
- Places all generated files inside this folder
- Automatically generates a requirements.txt file based on detected imports
- Maps import aliases to their proper PyPI package names (e.g., 'bs4' → 'beautifulsoup4')

## Auto-Save File Naming

When using the `--auto-save` flag, the script intelligently generates filenames based on:

1. **Class names**: If the code contains a class definition, the filename will be the snake_case version of the class name
2. **Function names**: If there's a function definition but no class, the filename will be the function name
3. **Prompt keywords**: If no class or function names are found, the filename will be derived from meaningful keywords in your prompt
4. **Fallback timestamp**: If all else fails, a timestamp-based filename will be used

This makes it easy to organize the generated code files logically without having to manually name each one.

## Troubleshooting

- **Error connecting to model server**: Make sure LM Studio is running and the API server is enabled.
- **Bad request errors**: Verify that the API URL is correct and the model accepts the format of requests being sent.
- **Empty or unexpected responses**: Check that your prompt is clear and appropriate for the model's capabilities.
- **Code formatting issues**: If the extracted code doesn't run correctly, try adjusting your prompt to be more specific about the code structure you need.
