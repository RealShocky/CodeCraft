This is your initial post to the IDE model to use our system (Copy this prompt below, paste to your IDE chat - If Using windsurf IDE, change to Cascase Base :)

I want to use my custom LLM integration script (custom_model.py) for our conversation. 
This script connects to a local LM Studio API running at http://localhost:1234/v1/chat/completions
and has these features:
- Clean code extraction and formatting
- Automatic code issue fixing including:
  - Moving imports to the top of the file
  - Reordering code for logical structure
  - Fixing duplicate functions and classes
  - Resolving common implementation issues
- Auto-saving to appropriate filenames
- Project organization:
  - Creating dedicated project folders
  - Generating requirements.txt files automatically
  - Organizing files within project folders
- Clipboard integration

Instead of using the default chat interface, please help me create prompts and run commands 
like this:
python custom_model.py -s -c --clean --fix --auto-save --project-folder "Your prompt here"

When I ask for code, assume I'm looking to generate it through this custom pipeline.
