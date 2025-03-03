import requests
import pyperclip
import sys
import json
import argparse
import os
import time
import re

try:
    from colorama import init, Fore, Style
    colorama_available = True
    init()  # Initialize colorama
except ImportError:
    colorama_available = False

def colored_print(text, color=None, style=None):
    """Print colored text if colorama is available"""
    if colorama_available:
        color_code = getattr(Fore, color.upper(), '') if color else ''
        style_code = getattr(Style, style.upper(), '') if style else ''
        reset = Style.RESET_ALL
        print(f"{color_code}{style_code}{text}{reset}")
    else:
        print(text)

def get_prompt(args):
    """Get the prompt from command line args or file"""
    if args.prompt:
        return args.prompt
    
    # Try to read from file
    file_path = args.file if args.file else 'prompt.txt'
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            prompt = f.read().strip()
            if not prompt:
                colored_print(f"Error: The file '{file_path}' is empty", 'red')
                return None
            return prompt
    except FileNotFoundError:
        colored_print(f"Error: File '{file_path}' not found", 'red')
        return None
    except Exception as e:
        colored_print(f"Error reading file: {e}", 'red')
        return None

def call_lm_studio_stream(prompt, args):
    """Call LM Studio API with streaming enabled"""
    api_url = args.api_url if args.api_url else "http://localhost:1234/v1/chat/completions"
    
    payload = {
        "messages": [{"role": "user", "content": prompt}],
        "temperature": args.temperature,
        "max_tokens": args.max_tokens,
        "stream": True
    }
    
    headers = {'Content-Type': 'application/json'}
    
    try:
        colored_print("Connecting to your API...", 'blue')
        
        # Create a buffer for the entire response
        full_text = ""
        buffer = ""
        
        # Open the connection and stream the response
        with requests.post(api_url, json=payload, headers=headers, stream=True) as response:
            response.raise_for_status()
            
            colored_print("\nModel Response:", 'green', 'bright')
            colored_print("-" * 40, 'green')
            
            for line in response.iter_lines():
                if line:
                    line_text = line.decode('utf-8')
                    
                    # Skip the "data: " prefix and process JSON
                    if line_text.startswith('data: '):
                        data_str = line_text[6:]  # Skip 'data: '
                        
                        # Check for the end of stream
                        if data_str == '[DONE]':
                            break
                            
                        try:
                            chunk = json.loads(data_str)
                            if 'choices' in chunk and len(chunk['choices']) > 0:
                                delta = chunk['choices'][0].get('delta', {})
                                if 'content' in delta:
                                    content = delta['content']
                                    print(content, end='', flush=True)
                                    full_text += content
                                    buffer += content
                        except json.JSONDecodeError:
                            pass  # Skip malformed JSON
            
            print("\n")  # Add newline after streaming completes
            colored_print("-" * 40, 'green')
            
            return full_text
            
    except requests.RequestException as e:
        colored_print(f"Error communicating with model server: {e}", 'red')
        if hasattr(e, 'response') and e.response is not None:
            colored_print(f"Response status code: {e.response.status_code}", 'red')
            try:
                colored_print(f"Response content: {e.response.text}", 'red')
            except:
                pass
        return None

def call_lm_studio_non_stream(prompt, args):
    """Call LM Studio API without streaming"""
    api_url = args.api_url if args.api_url else "http://localhost:1234/v1/chat/completions"
    
    payload = {
        "messages": [{"role": "user", "content": prompt}],
        "temperature": args.temperature,
        "max_tokens": args.max_tokens,
        "stream": False
    }
    
    headers = {'Content-Type': 'application/json'}
    
    try:
        colored_print("Connecting to LM Studio API...", 'blue')
        
        response = requests.post(api_url, json=payload, headers=headers)
        response.raise_for_status()
        
        data = response.json()
        
        # Extract the completion from the response
        if 'choices' in data and len(data['choices']) > 0:
            completion = data['choices'][0]['message']['content']
            
            colored_print("\nModel Response:", 'green', 'bright')
            colored_print("-" * 40, 'green')
            print(completion)
            colored_print("-" * 40, 'green')
            
            return completion
        else:
            colored_print("Unexpected response format:", 'red')
            colored_print(json.dumps(data, indent=2), 'yellow')
            return None
            
    except requests.RequestException as e:
        colored_print(f"Error communicating with model server: {e}", 'red')
        if hasattr(e, 'response') and e.response is not None:
            colored_print(f"Response status code: {e.response.status_code}", 'red')
            try:
                colored_print(f"Response content: {e.response.text}", 'red')
            except:
                pass
        return None

def extract_code_blocks(text, clean_output=False):
    """Extract code blocks from markdown text
    
    Args:
        text (str): Text containing code blocks
        clean_output (bool): If True, clean up the extracted code for execution
    
    Returns:
        str: Extracted and cleaned code
    """
    # First try to find code blocks with triple backticks
    code_blocks = re.findall(r'```(?:python)?\n([\s\S]*?)```', text)
    
    if code_blocks:
        code = '\n\n'.join(code_blocks)
        
        if clean_output:
            # Clean the code for execution
            code = clean_code_for_execution(code)
        
        return code
    
    # If no code blocks are found with backticks, try to extract indented code
    indented_blocks = re.findall(r'(?:^|\n)( {4}|\t)(.+)(?:\n|$)', text)
    if indented_blocks:
        code = '\n'.join(line[1] for line in indented_blocks)
        
        if clean_output:
            code = clean_code_for_execution(code)
            
        return code
    
    # If still no code found, try to use a more aggressive approach to find Python-like code
    if clean_output:
        # Try to extract Python-like patterns from the text
        maybe_code = extract_python_like_code(text)
        if maybe_code:
            return clean_code_for_execution(maybe_code)
        
        # If all else fails, clean the entire text
        return clean_code_for_execution(text)
    
    # If no code blocks are found, return the original text
    return text

def extract_python_like_code(text):
    """Extract Python-like code from text using heuristics
    
    This tries to identify Python code even when not in code blocks
    
    Args:
        text (str): Text that may contain Python code
        
    Returns:
        str: Extracted Python-like code or None if not found
    """
    # Look for common Python patterns
    python_patterns = [
        # Function definitions
        r'def\s+\w+\s*\([^)]*\):\s*(?:\n\s+.+)+',
        # Class definitions
        r'class\s+\w+(?:\([^)]*\))?:\s*(?:\n\s+.+)+',
        # If statements
        r'if\s+.+:\s*(?:\n\s+.+)+',
        # For loops
        r'for\s+.+:\s*(?:\n\s+.+)+',
        # Variable assignments with common Python types
        r'\w+\s*=\s*(?:[\'"]\w+[\'"]|\d+|\[.+\]|\{.+\}|\(.+\))'
    ]
    
    code_fragments = []
    
    for pattern in python_patterns:
        matches = re.findall(pattern, text)
        if matches:
            code_fragments.extend(matches)
    
    if code_fragments:
        # Sort the fragments based on their position in the original text
        positions = [(text.find(frag), frag) for frag in code_fragments if text.find(frag) >= 0]
        positions.sort()
        
        # Join the sorted fragments
        return '\n\n'.join(frag for _, frag in positions)
    
    return None

def clean_code_for_execution(code):
    """Clean the extracted code by removing interactive outputs and ensuring proper formatting
    
    This function makes the extracted code ready for execution by:
    1. Removing lines that look like interactive outputs or comments outside of functions
    2. Reordering functions and classes to ensure they're defined before they're used
    3. Moving imports to the top of the file
    
    Args:
        code (str): The code to clean
        
    Returns:
        str: Cleaned code ready for execution
    """
    # Remove lines that look like terminal output (not part of the code)
    lines = code.split('\n')
    cleaned_lines = []
    
    for line in lines:
        # Skip typical output lines and interactive Python prompts
        if (re.match(r'^(>>>|\.\.\.|In \[\d+\]:|Out\[\d+\]:)', line.strip()) or
            re.match(r'^(\[\d+\]:)', line.strip()) or  # IPython style output numbering
            re.match(r'^<(\w+) (object|at) .+>', line.strip())):  # Object representations
            continue
        
        cleaned_lines.append(line)
    
    # Rejoin the lines
    code = '\n'.join(cleaned_lines)
    
    # Try to reorder the code to ensure definitions come before usage
    code = reorder_code(code)
    
    # Move imports to the top
    code = move_imports_to_top(code)
    
    return code

def reorder_code(code):
    """Reorder code to ensure definitions come before usage
    
    This function tries to intelligently reorder code blocks so that classes and functions
    are defined before they're used, and the main block is at the end.
    
    Args:
        code (str): Code to reorder
        
    Returns:
        str: Reordered code
    """
    lines = code.split('\n')
    
    # Organize code into logical blocks
    code_blocks = []
    current_block = []
    in_function_def = False
    in_class_def = False
    in_docstring = False
    
    # First pass: divide code into logical blocks
    for i, line in enumerate(lines):
        line_stripped = line.strip()
        
        # Skip empty lines (we'll add proper spacing later)
        if not line_stripped:
            if current_block and i > 0 and not lines[i-1].strip():
                # Skip duplicate empty lines
                continue
            current_block.append('')
            continue
        
        # Handle common code patterns
        if re.match(r'^def\s+\w+\s*\(', line_stripped):
            # This is a function definition - start a new code block
            if current_block:
                code_blocks.append(current_block)
                current_block = []
            in_function_def = True
            current_block.append(line)
        elif re.match(r'^class\s+\w+', line_stripped):
            # This is a class definition - start a new code block
            if current_block:
                code_blocks.append(current_block)
                current_block = []
            in_class_def = True
            current_block.append(line)
        elif line_stripped.startswith('"""') or line_stripped.startswith("'''"):
            # This might be a docstring
            in_docstring = not in_docstring
            current_block.append(line)
        elif in_function_def or in_class_def or line_stripped.startswith('#'):
            # This is part of a function, class or a comment
            current_block.append(line)
        elif re.match(r'^if\s+__name__\s*==\s*[\'"]__main__[\'"]', line_stripped):
            # This is a main block - start a new code block
            if current_block:
                code_blocks.append(current_block)
                current_block = []
            current_block.append(line)
        else:
            # This could be a regular statement or part of a continuing block
            current_block.append(line)
    
    # Add the last block if there is one
    if current_block:
        code_blocks.append(current_block)
    
    # Organize blocks by type
    import_blocks = []
    class_blocks = []
    function_blocks = []
    main_blocks = []
    other_blocks = []
    
    for block in code_blocks:
        if not block:
            continue
            
        first_line = block[0].strip()
        is_import_block = True
        
        # Check if this is an import block
        for line in block:
            stripped = line.strip()
            if stripped and not (stripped.startswith('import ') or 
                               (stripped.startswith('from ') and ' import ' in stripped) or
                               not stripped):
                is_import_block = False
                break
        
        if is_import_block and any(line.strip() for line in block):
            import_blocks.append(block)
        elif first_line.startswith('class '):
            class_blocks.append(block)
        elif first_line.startswith('def '):
            function_blocks.append(block)
        elif first_line.startswith('if __name__'):
            main_blocks.append(block)
        else:
            other_blocks.append(block)
    
    # Rebuild the code in a logical order
    ordered_blocks = import_blocks + class_blocks + function_blocks + other_blocks + main_blocks
    
    # Join blocks with appropriate spacing
    final_lines = []
    for i, block in enumerate(ordered_blocks):
        if i > 0 and block:  # Add a blank line between blocks
            final_lines.append('')
        final_lines.extend(block)
    
    # Final cleanup - ensure consistent whitespace
    cleaned_lines = []
    for line in final_lines:
        # Remove extra spaces at the end of lines
        cleaned_lines.append(line.rstrip())
    
    # Join the cleaned lines with newlines
    reordered_code = '\n'.join(cleaned_lines)
    
    # Ensure code ends with a newline
    if reordered_code and not reordered_code.endswith('\n'):
        reordered_code += '\n'
        
    return reordered_code

def move_imports_to_top(code):
    """Move import statements to the top of the file
    
    This function detects import statements that appear in the middle or
    at the bottom of the file and moves them to the top.
    
    Args:
        code (str): The code to fix
        
    Returns:
        str: Fixed code with imports at the top
    """
    lines = code.split('\n')
    
    # Find all import statements
    import_lines = []
    non_import_lines = []
    
    for line in lines:
        stripped = line.strip()
        # Match both 'import x' and 'from x import y' statements
        if (stripped.startswith('import ') or 
            (stripped.startswith('from ') and ' import ' in stripped)):
            import_lines.append(line)
        else:
            non_import_lines.append(line)
    
    # If there are no imports, return the original code
    if not import_lines:
        return code
    
    # Group imports: standard library first, then third-party, then local
    std_lib_imports = []
    third_party_imports = []
    local_imports = []
    
    std_lib_modules = [
        'abc', 'argparse', 'array', 'ast', 'asyncio', 'base64', 'bisect', 'calendar',
        'collections', 'concurrent', 'contextlib', 'copy', 'csv', 'datetime', 'decimal',
        'difflib', 'enum', 'errno', 'fnmatch', 'functools', 'gc', 'glob', 'gzip', 'hashlib',
        'heapq', 'hmac', 'html', 'http', 'importlib', 'inspect', 'io', 'itertools', 'json',
        'logging', 'math', 'multiprocessing', 'operator', 'os', 'pathlib', 'pickle', 'platform',
        'pprint', 'queue', 'random', 're', 'shutil', 'signal', 'socket', 'sqlite3', 'ssl',
        'statistics', 'string', 'struct', 'subprocess', 'sys', 'tempfile', 'threading',
        'time', 'timeit', 'traceback', 'types', 'typing', 'uuid', 'warnings', 'weakref',
        'xml', 'xmlrpc', 'zipfile', 'zlib'
    ]
    
    # Categorize imports
    for line in import_lines:
        stripped = line.strip()
        
        # Extract module name
        if stripped.startswith('from '):
            module = stripped.split('from ')[1].split(' import')[0].split('.')[0]
        else:
            module = stripped.split('import ')[1].split(' as ')[0].split(',')[0].strip()
        
        # Categorize by module type
        if module in std_lib_modules:
            std_lib_imports.append(line)
        elif module.startswith('.'):
            local_imports.append(line)
        else:
            third_party_imports.append(line)
    
    # Combine imports in the right order with proper spacing
    all_imports = std_lib_imports + [''] + third_party_imports + [''] + local_imports
    # Remove empty items if a category has no imports
    all_imports = [imp for imp in all_imports if imp != ''] or ['']
    
    # Join everything back with imports at the top
    # Add a blank line after imports if there isn't one already
    if all_imports and non_import_lines and non_import_lines[0].strip():
        all_imports.append('')
    
    result = '\n'.join(all_imports + non_import_lines)
    return result

def generate_filename_from_content(code, prompt):
    """Generate a suitable filename based on code content or prompt
    
    Args:
        code (str): The extracted code
        prompt (str): The original prompt
        
    Returns:
        str: A suitable filename (with .py extension)
    """
    # Try to extract a class or function name from the code
    class_match = re.search(r'class\s+(\w+)', code)
    function_match = re.search(r'def\s+(\w+)', code)
    
    if class_match:
        # Convert CamelCase to snake_case for filename
        name = class_match.group(1)
        filename = ''.join(['_' + c.lower() if c.isupper() else c for c in name]).lstrip('_')
        return f"{filename}.py"
    elif function_match:
        return f"{function_match.group(1)}.py"
    else:
        # Try to extract a meaningful name from the prompt
        words = prompt.lower().split()
        # Remove common words and keep only the most relevant ones
        common_words = {'a', 'an', 'the', 'to', 'in', 'for', 'of', 'and', 'with', 'that', 'write', 'create', 'implement', 'python', 'function', 'class', 'code'}
        relevant_words = [w for w in words if w not in common_words and len(w) > 2]
        
        if relevant_words:
            # Use up to 3 words for the filename
            name = '_'.join(relevant_words[:3])
            # Cleanup any non-alphanumeric characters
            name = re.sub(r'[^a-z0-9_]', '', name)
            return f"{name}.py"
        else:
            # Default name with timestamp
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            return f"code_{timestamp}.py"

def fix_common_code_issues(code):
    """Fix common issues in generated code
    
    This function attempts to fix common issues in LLM-generated code, such as:
    - Duplicate class/function definitions
    - Missing method implementations
    - Incomplete class definitions
    
    Args:
        code (str): The code to fix
        
    Returns:
        str: Fixed code
    """
    lines = code.split('\n')
    class_defs = {}  # Store class names and their line numbers
    method_defs = {}  # Store method names and their line numbers
    fixed_lines = []
    
    # First pass: identify duplicate definitions and track classes and methods
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        # Check for class definitions
        class_match = re.match(r'^class\s+(\w+)', line)
        if class_match:
            class_name = class_match.group(1)
            if class_name in class_defs:
                # Skip duplicate class definition
                # Find where this class definition ends
                j = i + 1
                indent_level = 0
                while j < len(lines) and (not lines[j].strip() or lines[j].startswith(' ') or lines[j].startswith('\t')):
                    j += 1
                i = j  # Skip to the end of this duplicate class
                continue
            else:
                class_defs[class_name] = i
        
        # Check for method definitions
        method_match = re.match(r'^\s*def\s+(\w+)', line)
        if method_match:
            method_name = method_match.group(1)
            # Check if this is a duplicate method in the same class
            current_class = None
            for cls, line_num in class_defs.items():
                if line_num < i:
                    current_class = cls
            
            method_key = f"{current_class}.{method_name}" if current_class else method_name
            
            if method_key in method_defs and method_name != "__init__":
                # Skip duplicate method definition
                # Find where this method definition ends
                j = i + 1
                indent_level = len(lines[i]) - len(lines[i].lstrip())
                while j < len(lines) and (not lines[j].strip() or len(lines[j]) - len(lines[j].lstrip()) > indent_level):
                    j += 1
                i = j  # Skip to the end of this duplicate method
                continue
            else:
                method_defs[method_key] = i
        
        fixed_lines.append(lines[i])
        i += 1
    
    # Convert back to text for the second pass
    code = '\n'.join(fixed_lines)
    
    # Second pass: fix specific common patterns
    # 1. Fix incomplete Node class
    code = fix_incomplete_node_class(code)
    
    # 2. Fix duplicate __init__ methods
    code = fix_duplicate_init_methods(code)
    
    return code

def fix_incomplete_node_class(code):
    """Fix a common issue where a Node class is incomplete or malformed
    
    This is often seen in BST implementations where a Node class is declared
    but lacks proper initialization or has attributes in a separate class
    
    Args:
        code (str): The code to fix
        
    Returns:
        str: Fixed code
    """
    lines = code.split('\n')
    
    # Check if there's a TreeNode class and a BinarySearchTree class with similar attributes
    tree_node_match = re.search(r'class\s+(TreeNode|Node)\s*:', code)
    bst_match = re.search(r'class\s+(BinarySearchTree|BST)\s*:', code)
    
    if tree_node_match and bst_match:
        tree_node_class = tree_node_match.group(1)
        bst_class = bst_match.group(1)
        
        # Check for common issue where BST has TreeNode-like init
        bst_init_with_key = re.search(
            rf'class\s+{bst_class}\s*:.*?def\s+__init__\s*\(\s*self\s*,\s*(?:key|val|value).*?\)',
            code, re.DOTALL)
        
        # Check for empty TreeNode class
        empty_treenode = re.search(
            rf'class\s+{tree_node_class}\s*:(?:\s*\n\s*|$)', 
            code)
        
        if bst_init_with_key and empty_treenode:
            # The BST class has a TreeNode-like init, and TreeNode is empty
            # This is a common pattern where the model duplicated functionality
            
            # First, find the BST init
            bst_init_start = bst_init_with_key.start()
            
            # Find which line has the BST init
            line_count = 0
            bst_init_line = 0
            for i, line in enumerate(lines):
                line_count += len(line) + 1  # +1 for newline
                if line_count > bst_init_start:
                    bst_init_line = i
                    break
            
            # Find the indentation of the init method
            bst_init_indent = len(lines[bst_init_line]) - len(lines[bst_init_line].lstrip())
            
            # Find the end of the init method
            j = bst_init_line + 1
            while j < len(lines) and (not lines[j].strip() or len(lines[j]) - len(lines[j].lstrip()) > bst_init_indent):
                j += 1
            
            # Extract the BST init method
            bst_init_method = '\n'.join(lines[bst_init_line:j])
            
            # Now check if we can find a proper TreeNode init that could work
            proper_node_init = re.search(
                rf'def\s+__init__\s*\(\s*self\s*,\s*(?:key|val|value).*?\).*?self\.(?:key|val|value)\s*=\s*(?:key|val|value)',
                code, re.DOTALL)
            
            if proper_node_init:
                # We found a proper TreeNode init elsewhere, extract and use it
                node_init_start = proper_node_init.start()
                
                # Find which line has the proper node init
                line_count = 0
                node_init_line = 0
                for i, line in enumerate(lines):
                    line_count += len(line) + 1  # +1 for newline
                    if line_count > node_init_start:
                        node_init_line = i
                        break
                
                # Find the indentation of the init method
                node_init_indent = len(lines[node_init_line]) - len(lines[node_init_line].lstrip())
                
                # Find the end of the init method
                j = node_init_line + 1
                while j < len(lines) and (not lines[j].strip() or len(lines[j]) - len(lines[j].lstrip()) > node_init_indent):
                    j += 1
                
                # Extract the proper node init method
                proper_node_init_method = '\n'.join(lines[node_init_line:j])
                
                # Update the TreeNode class with the proper init
                tree_node_pattern = rf'class\s+{tree_node_class}\s*:(?:\s*\n\s*|$)'
                # Make sure to indent the init method correctly
                indented_init = proper_node_init_method.replace('def ', '    def ')
                replacement = f'class {tree_node_class}:\n{indented_init}\n'
                
                code = re.sub(tree_node_pattern, replacement, code)
                
                # Now fix the BST class to have a proper init without the TreeNode attributes
                bst_pattern = rf'class\s+{bst_class}\s*:.*?def\s+__init__\s*\(\s*self\s*,\s*(?:key|val|value).*?\)(.*?)(?:\n\s*def|\n\s*$)'
                replacement = f'class {bst_class}:\n    def __init__(self):\n        self.root = None\n'
                
                code = re.sub(bst_pattern, replacement, code, flags=re.DOTALL)
            else:
                # No proper TreeNode init found, create one from the BST init
                # First, fix the BST init to be a proper BST init
                bst_pattern = rf'class\s+{bst_class}\s*:.*?def\s+__init__\s*\(\s*self\s*,\s*(?:key|val|value).*?\)(.*?)(?:\n\s*def|\n\s*$)'
                replacement = f'class {bst_class}:\n    def __init__(self):\n        self.root = None\n'
                
                code = re.sub(bst_pattern, replacement, code, flags=re.DOTALL)
                
                # Now create a proper TreeNode init from the BST init
                tree_node_pattern = rf'class\s+{tree_node_class}\s*:(?:\s*\n\s*|$)'
                # Extract the key parameter name from the BST init
                key_param = re.search(r'def\s+__init__\s*\(\s*self\s*,\s*(\w+)', bst_init_method)
                key_param = key_param.group(1) if key_param else 'key'
                
                # Use the BST init attributes for TreeNode
                attributes = []
                for attr in ['key', 'val', 'value', 'left', 'right']:
                    if re.search(rf'self\.{attr}\s*=', bst_init_method):
                        if attr in ['key', 'val', 'value']:
                            attributes.append(f'self.{attr} = {key_param}')
                        else:
                            attributes.append(f'self.{attr} = None')
                
                # If no attributes found, use default attributes
                if not attributes:
                    attributes = [f'self.key = {key_param}', 'self.left = None', 'self.right = None']
                
                # Create the TreeNode init
                indented_attributes = '\n        '.join(attributes)
                replacement = f'class {tree_node_class}:\n    def __init__(self, {key_param}):\n        {indented_attributes}\n'
                
                code = re.sub(tree_node_pattern, replacement, code)
    
    return code

def fix_duplicate_init_methods(code):
    """Fix duplicate __init__ methods in the same class
    
    Args:
        code (str): The code to fix
        
    Returns:
        str: Fixed code
    """
    lines = code.split('\n')
    class_name = None
    init_methods = {}  # class_name -> list of (line_number, end_line, code)
    i = 0
    
    # Find all init methods
    while i < len(lines):
        line = lines[i].strip()
        
        # Track class definitions
        class_match = re.match(r'^class\s+(\w+)', line)
        if class_match:
            class_name = class_match.group(1)
        
        # Check for __init__ method
        init_match = re.match(r'^\s*def\s+__init__\s*\(', line)
        if init_match and class_name:
            # This is an __init__ method in a class
            start_line = i
            init_indent = len(lines[i]) - len(lines[i].lstrip())
            
            # Find the end of the init method
            j = i + 1
            while j < len(lines) and (not lines[j].strip() or len(lines[j]) - len(lines[j].lstrip()) > init_indent):
                j += 1
            
            # Store this init method
            if class_name not in init_methods:
                init_methods[class_name] = []
            
            init_methods[class_name].append((start_line, j, '\n'.join(lines[start_line:j])))
            
            i = j
            continue
        
        i += 1
    
    # Now, fix classes with multiple init methods
    for class_name, inits in init_methods.items():
        if len(inits) > 1:
            # Multiple init methods found
            # Strategy: Keep the most complex one (usually the one with more parameters or lines)
            best_init = max(inits, key=lambda x: (len(x[2].split(',')), len(x[2].split('\n'))))
            
            # Remove all but the best init
            to_remove = [init for init in inits if init != best_init]
            
            # Sort in reverse order to avoid changing line numbers
            to_remove.sort(key=lambda x: x[0], reverse=True)
            
            for start, end, _ in to_remove:
                lines = lines[:start] + lines[end:]
    
    return '\n'.join(lines)

def generate_project_name(prompt, code):
    """Generate a project name from the prompt or code
    
    Args:
        prompt (str): The prompt used to generate the code
        code (str): The generated code
        
    Returns:
        str: A suitable project name
    """
    # Extract key terms from the prompt
    keywords = re.findall(r'\b[a-zA-Z][a-zA-Z0-9_]{2,}\b', prompt.lower())
    
    # Filter out common words
    common_words = {'the', 'and', 'that', 'with', 'for', 'create', 'implement', 'build', 'make', 'code', 'write', 'script', 'program', 'python'}
    keywords = [word for word in keywords if word not in common_words]
    
    # If we have keywords, use those to create a name
    if keywords:
        project_name = '_'.join(keywords[:3])  # Use up to 3 keywords
    else:
        # Fall back to the content-based naming
        project_name = generate_filename_from_content(code, prompt).replace('.py', '')
    
    # Ensure the name is a valid directory name
    project_name = re.sub(r'[^\w_]', '_', project_name)
    
    # Limit length and make it more readable
    if len(project_name) > 30:
        project_name = project_name[:30]
    
    return project_name

def generate_requirements_file(code, project_dir):
    """Generate a requirements.txt file based on the imports in the code
    
    Args:
        code (str): The code to analyze for imports
        project_dir (str): The directory to save the requirements.txt file
    """
    # Extract all import statements
    import_lines = []
    for line in code.split('\n'):
        line = line.strip()
        if line.startswith('import ') or (line.startswith('from ') and ' import ' in line):
            import_lines.append(line)
    
    # Extract package names from import statements
    packages = set()
    for line in import_lines:
        if line.startswith('import '):
            # Handle 'import package' and 'import package1, package2'
            parts = line[7:].split(',')
            for part in parts:
                # Handle 'import package as alias'
                package = part.split(' as ')[0].strip()
                # Get the main package (before any dot)
                main_package = package.split('.')[0]
                packages.add(main_package)
        else:  # from X import Y
            # Handle 'from package import ...'
            package = line.split('from ')[1].split(' import')[0].strip()
            # Get the main package (before any dot)
            main_package = package.split('.')[0]
            packages.add(main_package)
    
    # Filter out standard library packages
    std_lib_modules = {
        'abc', 'argparse', 'array', 'ast', 'asyncio', 'base64', 'bisect', 'calendar',
        'collections', 'concurrent', 'contextlib', 'copy', 'csv', 'datetime', 'decimal',
        'difflib', 'enum', 'errno', 'fnmatch', 'functools', 'gc', 'glob', 'gzip', 'hashlib',
        'heapq', 'hmac', 'html', 'http', 'importlib', 'inspect', 'io', 'itertools', 'json',
        'logging', 'math', 'multiprocessing', 'operator', 'os', 'pathlib', 'pickle', 'platform',
        'pprint', 'queue', 'random', 're', 'shutil', 'signal', 'socket', 'sqlite3', 'ssl',
        'statistics', 'string', 'struct', 'subprocess', 'sys', 'tempfile', 'threading',
        'time', 'timeit', 'traceback', 'types', 'typing', 'uuid', 'warnings', 'weakref',
        'xml', 'xmlrpc', 'zipfile', 'zlib', 'tkinter', 'tk', 'ttk'
    }
    
    third_party_packages = packages - std_lib_modules
    
    # Map common package imports to their PyPI names
    package_mapping = {
        'bs4': 'beautifulsoup4',
        'sklearn': 'scikit-learn',
        'PIL': 'pillow',
        'cv2': 'opencv-python',
        'pygame': 'pygame',
        'np': 'numpy',
        'pd': 'pandas',
        'plt': 'matplotlib',
        'tf': 'tensorflow',
        'torch': 'torch',
        'db': 'sqlalchemy',
    }
    
    # Apply the mapping
    requirements = []
    for pkg in third_party_packages:
        if pkg in package_mapping:
            requirements.append(package_mapping[pkg])
        else:
            requirements.append(pkg)
    
    # Sort the requirements alphabetically
    requirements.sort()
    
    # Write the requirements to a file
    if requirements:
        try:
            with open(os.path.join(project_dir, 'requirements.txt'), 'w') as f:
                f.write('\n'.join(requirements))
            print(Fore.GREEN + "Generated requirements.txt file with detected dependencies")
        except Exception as e:
            print(Fore.RED + f"Error creating requirements.txt: {e}")

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Interact with LM Studio API')
    parser.add_argument('prompt', nargs='?', help='Prompt text (if not provided, reads from file)')
    parser.add_argument('-f', '--file', help='Path to prompt file (default: prompt.txt)')
    parser.add_argument('-u', '--api-url', help='LM Studio API URL (default: http://localhost:1234/v1/chat/completions)')
    parser.add_argument('-t', '--temperature', type=float, default=0.7, help='Temperature for generation (default: 0.7)')
    parser.add_argument('-m', '--max-tokens', type=int, default=2000, help='Maximum tokens to generate (default: 2000)')
    parser.add_argument('-s', '--stream', action='store_true', help='Use streaming API for real-time responses')
    parser.add_argument('-n', '--no-copy', action='store_true', help='Do not copy response to clipboard')
    parser.add_argument('-c', '--code-only', action='store_true', help='Extract and copy only code blocks from response')
    parser.add_argument('--clean', action='store_true', help='Clean extracted code for execution')
    parser.add_argument('-o', '--output', help='Save extracted code to the specified file')
    parser.add_argument('--auto-save', action='store_true', help='Automatically save code to a file with an inferred name')
    parser.add_argument('--fix', action='store_true', help='Attempt to fix common issues in generated code')
    parser.add_argument('--project-folder', action='store_true', help='Create a project folder for generated files')
    
    args = parser.parse_args()
    
    # Get prompt
    prompt = get_prompt(args)
    if not prompt:
        return
    
    # Display prompt
    colored_print("\nSending prompt:", 'blue', 'bright')
    print(f'"{prompt}"')
    
    # Call LM Studio API
    start_time = time.time()
    
    if args.stream:
        completion = call_lm_studio_stream(prompt, args)
    else:
        completion = call_lm_studio_non_stream(prompt, args)
        
    end_time = time.time()
    
    if completion:
        # Process completion
        if args.code_only:
            code_only = extract_code_blocks(completion, clean_output=args.clean)
            if code_only != completion:
                colored_print("\nExtracted code:", 'blue', 'bright')
                print(code_only)
                completion_to_copy = code_only
            else:
                completion_to_copy = completion
        else:
            completion_to_copy = completion
            if args.clean:
                # Still clean the output even if not extracting code blocks
                completion_to_copy = clean_code_for_execution(completion_to_copy)
        
        # Fix common code issues if requested
        if args.fix:
            original_code = completion_to_copy
            completion_to_copy = fix_common_code_issues(completion_to_copy)
            if original_code != completion_to_copy:
                colored_print("\nFixed common code issues", 'green')
        
        # Copy to clipboard
        if not args.no_copy:
            pyperclip.copy(completion_to_copy)
            colored_print("\nResponse copied to clipboard", 'blue')
            if args.code_only:
                colored_print("(Code blocks only)", 'blue')
            if args.clean:
                colored_print("(Cleaned for execution)", 'blue')
            if args.fix:
                colored_print("(Fixed common issues)", 'blue')
        
        # Save to file if specified
        if args.output or args.auto_save:
            file_path = args.output
            
            # Generate a filename based on the prompt if auto-save is enabled
            if args.auto_save and not file_path:
                # Extract a suitable filename from the first line of code or the prompt
                file_path = generate_filename_from_content(completion_to_copy, prompt)
            
            if file_path:
                try:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(completion_to_copy)
                    colored_print(f"\nCode saved to file: {file_path}", 'green')
                    
                    # Create a project folder if requested
                    if args.project_folder:
                        project_name = generate_project_name(prompt, completion_to_copy)
                        project_dir = os.path.join(os.getcwd(), project_name)
                        
                        # Create project directory if it doesn't exist
                        if not os.path.exists(project_dir):
                            try:
                                os.makedirs(project_dir)
                                colored_print(f"\nCreated project folder: {project_name}", 'green')
                            except Exception as e:
                                colored_print(f"\nError creating project folder: {e}", 'red')
                                project_dir = os.getcwd()  # Fallback to current directory
                        
                        # Move the saved file to the project folder
                        try:
                            os.replace(file_path, os.path.join(project_dir, os.path.basename(file_path)))
                            colored_print(f"\nMoved file to project folder: {project_name}", 'green')
                        except Exception as e:
                            colored_print(f"\nError moving file to project folder: {e}", 'red')
                        
                        # Generate requirements.txt if project folder is created
                        generate_requirements_file(completion_to_copy, project_dir)
                except Exception as e:
                    colored_print(f"\nError saving to file: {e}", 'red')
        
        # Show stats
        elapsed = end_time - start_time
        colored_print(f"\nResponse time: {elapsed:.2f} seconds", 'blue')
        token_count = len(completion.split())
        colored_print(f"Approximate response tokens: {token_count}", 'blue')

if __name__ == '__main__':
    main()