import os
from dotenv import find_dotenv, load_dotenv
from datetime import datetime
import json
import openai
from tenacity import (
    retry,
    stop_after_attempt,
    wait_random_exponential,
)
import tiktoken

CHAT_HISTORY_DIR = "history"
load_dotenv(find_dotenv())


class ChatModel:
    """Functionality to have a conversation with gpt. Automates storage of memory"""
    def __init__(
            self,
            api_key=os.environ.get("OPENAI_API_KEY"),
            organisation=os.environ.get("OPENAI_ORGANIZATION"),
            model="gpt-3.5-turbo",
            role="You are a helpful assistant",
    ):
        self.api_key=api_key
        if organisation is not None:
            self.organisation = organisation
        elif "OPENAI_ORGANIZATION" in os.environ:
            self.organisation = os.environ.get("OPENAI_ORGANIZATION")
        else:
            self.organisation = None
        self.model = model
        self.chat_history = [{"role": "system", "content": role}]

    def num_tokens_from_messages(self, messages=None, model=None, new_user_message=None):
        """Return the number of tokens used by a list of messages."""
        if model is None:
            model = self.model
        if messages is None:
            messages = self.chat_history
        try:
            encoding = tiktoken.encoding_for_model(model)
        except KeyError:
            print("Warning: model not found. Using cl100k_base encoding.")
            encoding = tiktoken.get_encoding("cl100k_base")
        if model in {
            "gpt-3.5-turbo-0613",
            "gpt-3.5-turbo-16k-0613",
            "gpt-4-0314",
            "gpt-4-32k-0314",
            "gpt-4-0613",
            "gpt-4-32k-0613",
        }:
            tokens_per_message = 3
            tokens_per_name = 1
        elif model == "gpt-3.5-turbo-0301":
            tokens_per_message = 4  # every message follows <|start|>{role/name}\n{content}<|end|>\n
            tokens_per_name = -1  # if there's a name, the role is omitted
        elif "gpt-3.5-turbo" in model:
            print("Warning: gpt-3.5-turbo may update over time. Returning num tokens assuming gpt-3.5-turbo-0613.")
            return self.num_tokens_from_messages(messages, model="gpt-3.5-turbo-0613")
        elif "gpt-4" in model:
            print("Warning: gpt-4 may update over time. Returning num tokens assuming gpt-4-0613.")
            return self.num_tokens_from_messages(messages, model="gpt-4-0613")
        else:
            raise NotImplementedError(
                f"""num_tokens_from_messages() is not implemented for model {model}. See https://github.com/openai/openai-python/blob/main/chatml.md for information on how messages are converted to tokens."""
            )

        if new_user_message:
            self.add_to_memory("user", new_user_message)
        else:
            num_tokens = 0
        for message in messages:
            num_tokens += tokens_per_message
            for key, value in message.items():
                num_tokens += len(encoding.encode(value))
                if key == "name":
                    num_tokens += tokens_per_name
        num_tokens += 3  # every reply is primed with <|start|>assistant<|message|>
        if new_user_message:
            self.chat_history = self.chat_history[:-1]
        return num_tokens

    @retry(wait=wait_random_exponential(min=1, max=20), stop=stop_after_attempt(6))
    def get_completion(self, input_text: str, model=None, max_tokens=None) -> str:
        """takes input text, stores it in chat history, and sends chat history via api. Stores
        the response to chat history and returns response"""
        model = self.model if model is None else model
        self.chat_history.append({"role": "user", "content": input_text})
        response = openai.ChatCompletion.create(
            model=model,
            api_key=self.api_key,
            organization=self.organisation,
            messages=self.chat_history,
            max_tokens=max_tokens
        )
        response_message = response.choices[0].message.content
        self.add_to_memory(response_message, "assistant")
        return response_message

    def add_to_memory(self, message: str, role: str, enforce_order = True):
        """Adds either user or assistant message to chat memory"""
        if enforce_order:
            if role not in ["user", "assistant", "system"]:
                raise ValueError("Chose either user or assistant or system")
            if role == self.chat_history[-1]["role"]:
                raise ValueError("the last message in chat was made by {}. You cannot add this role".format(role))
            if role == "assistant" and len(self.chat_history) == 1:
                raise ValueError("you cannot start the conversation as assistant")

        self.chat_history.append({"role": role, "content": message})


    def __call__(self, input_text: str):
        return self.get_completion(input_text)

    def save_chat_history(self, filename=None):
        if filename is None:
            now = datetime.now()
            timestamp_str = now.strftime("%Y-%m-%d_%H-%M-%S")
            filename = f"chat_{timestamp_str}.json"

        path = os.path.join(CHAT_HISTORY_DIR,filename)
        with open(path, 'w') as f:
            json.dump(self.chat_history, f)

    def import_chat_history(self, filename):
        file = os.path.join(CHAT_HISTORY_DIR, filename)
        with open(file, "r") as f:
            self.chat_history = json.load(f)

class MultiUserChatModel(ChatModel):
    default_role = """You are engaged in a conversation with two people called Mary and Paul. Mary's statements start with
     'Mary:', Pauls with 'Paul:'. You are to decide whether to add to the conversation now or to continue listening. 
     If you choose to add now simply say what you want to say. Otherwise respond with ###continue###. A ###continue### 
     message MUST never include anything other than ###contineu###. If the participants address you, you must respond.
     When you are clearly addressed, definitely respond. If you feel the two need your help, respond. 
      Remember you are not to talk as though you were one of the participants. You are an AI involved in the conversation"""
    def __init__(
            self,
            api_key = os.environ.get("OPENAI_API_KEY"),
            organisation = os.environ.get("OPENAI_ORGANIZATION"),
            model="gpt-3.5-turbo",
            system_prompt = default_role,
            instruction_prompt = None,
            evaluate_agreement_prompt = None,

    ):
        super().__init__(api_key, organisation, model, system_prompt)
        self.instruction_prompt = instruction_prompt
        self.evaluate_agreement_prompt = evaluate_agreement_prompt

    @retry(wait=wait_random_exponential(min=1, max=20), stop=stop_after_attempt(6))
    def get_completion(self, input_text: str, model=None, evaluate_agreement=False) -> str:
        model = self.model if model is None else model
        if input_text == "init":
            self.add_to_memory(
                message="""introduce yourself briefly and welcome your clients to the session. 80 tokens max.
                Don't explicitly state your approach now.""",
                role="system",
                enforce_order=False
            )
        else:
            self.add_to_memory(message=input_text, role="user", enforce_order=False)
            if evaluate_agreement:
                prompt = self.evaluate_agreement_prompt
            else:
                prompt = self.instruction_prompt
            self.add_to_memory(message=prompt, role="system")
        response = openai.ChatCompletion.create(
            model=model,
            api_key=self.api_key,
            organization=self.organisation,
            messages=self.chat_history,
        )
        response_message = response.choices[0].message.content
        self.chat_history = self.chat_history[:-1]

        if response_message != "###continue###":
            self.add_to_memory(message=response_message, role="assistant", enforce_order=False)

        return response_message

    def __call__(self, input_text: str, model=None, evaluate_agreement=False):
        return self.get_completion(input_text, model=model, evaluate_agreement=evaluate_agreement)


class SimpleCompletion():
    def __init__(
            self,
            api_key=os.environ.get("OPENAI_API_KEY"),
            organisation=os.environ.get("OPENAI_ORGANIZATION"),
            model="gpt-3.5-turbo",
            role="You are a helpful assistant",
    ):
        self.api_key=api_key
        if organisation is not None:
            self.organisation = organisation
        elif "OPENAI_ORGANIZATION" in os.environ:
            self.organisation = os.environ.get("OPENAI_ORGANIZATION")
        else:
            self.organisation = None
        self.model = model
        self.chat_history = [{"role": "system", "content": role}]

    @retry(wait=wait_random_exponential(min=1, max=20), stop=stop_after_attempt(6))
    def get_completion(self, input_text: str, model=None, max_tokens=None) -> str:
        model = self.model if model is None else model
        self.chat_history.append({"role": "user", "content": input_text})
        response = openai.ChatCompletion.create(
            model=model,
            api_key=self.api_key,
            organization=self.organisation,
            messages=self.chat_history,
            max_tokens=max_tokens
        )
        response_message = response.choices[0].message.content
        return response_message

    def __call__(self, input_text: str):
        return self.get_completion(input_text)
