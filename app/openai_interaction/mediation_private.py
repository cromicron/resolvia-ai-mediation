from app.openai_interaction import ChatModel
from prompts import exploration_prompt
import re

mediator = ChatModel(role=exploration_prompt.format("None yet"))

def send_request_to_openai(content):
    n_tokens = mediator.num_tokens_from_messages(new_user_message=content)
    if mediator.model == "gpt-3.5-turbo":
        if n_tokens < 4097:
            return mediator(content)
        else:
            model = "gpt-3.5-turbo-16k"
            return mediator(content, model=model)
    else:
        if n_tokens < 8191:
            return mediator(content)
        else:
            model = "gpt-4-32k"
            return mediator(content, model=model)


def extract_initial_statement():
    """extracts conflict statement from gpt-output and replaces current conflict statement in the history."""
    pattern = r"###start_statement###(.*?)###end_statement###"
    last_output = mediator.chat_history[-1]["content"]
    match = re.search(pattern, last_output, re.DOTALL)
    if match:
        return match.group(1)
    else:
        return None

def end_first_session():
    """saves chat history"""
    mediator.save_chat_history()
