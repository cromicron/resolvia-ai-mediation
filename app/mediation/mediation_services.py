
from app.openai_interaction.ChatModel import ChatModel, MultiUserChatModel, SimpleCompletion
from app.openai_interaction.prompts import (
    exploration_prompt,
    mediation_prompt,
    mediation_prompt_instruct,
    evaluate_agreement_prompt,
    agreement_title_prompt
)
from app import db
from app.models import User, Mediation, MessagePrivate, MessagePublic, Agreement
import re
import copy


class PrivateMediation:
    """Handels all interations with OpenAI for Private Mediation"""
    def __init__(self, mediation_id, user_id, load_from_db = False, model="gpt-3.5-turbo"):

        self.mediation_id = mediation_id
        self.user_id = user_id
        self.mediation_db = Mediation.query.get_or_404(mediation_id)
        self.mediator = ChatModel(role=exploration_prompt, model=model)
        self.current_conflict_statement = None
        if load_from_db:
            messages = MessagePrivate.query.filter_by(
                user_id=user_id,
                mediation_id=mediation_id
            ).order_by(MessagePrivate.sequence_number).all()

            matching_indices = []

            # Add messages to chat history and record the indices of matching system messages
            for index, message in enumerate(messages):
                self.mediator.add_to_memory(message=message.content, role=message.role)

                if message.role == 'system' and message.content.startswith(
                        "the current conflict statement has been updated to"):
                    matching_indices.append(index)

            # Modify the content for all but the last matching system message
            for i in matching_indices[:-1]:  # Exclude the last index
                self.mediator.chat_history[i]["content"] = "conflict statement update"

            print(self.mediator.chat_history)

    def send_request_to_openai(self, content):
        n_tokens = self.mediator.num_tokens_from_messages(new_user_message=content)
        if self.mediator.model == "gpt-3.5-turbo":
            if n_tokens < 4097:
                return self.mediator(content)
            else:
                model = "gpt-3.5-turbo-16k"
                return self.mediator(content, model=model)
        else:
            if n_tokens < 8191:
                return self.mediator(content)
            else:
                model = "gpt-4-32k"
                return self.mediator(content, model=model)

    def extract_initial_statement(self):
        """Extracts conflict statement from gpt-output, replaces current conflict statement in the history, removes the matched pattern from the last output and deletes old system messages about updating the conflict statement."""

        pattern = r"###start_statement###(.*?)###end_statement###"
        last_output = self.mediator.chat_history[-1]["content"]
        match = re.search(pattern, last_output, re.DOTALL)

        if match:
            extracted_statement = match.group(1).strip()  # Extracted conflict statement

            # Replace the matched pattern with an empty string in the last output
            self.mediator.chat_history[-1]["content"] = re.sub(pattern, '', last_output, flags=re.DOTALL).strip()
            # TODO if empty content, delete from history or add some content like look at the statement on the right
            # Remove all old system messages that indicate an updated conflict statement
            update_message = "the current conflict statement has been updated to:"
            self.mediator.chat_history = [msg for msg in self.mediator.chat_history if
                                          not (msg['role'] == 'system' and update_message in msg['content'])]

            # Add a new system message indicating the updated conflict statement
            self.mediator.add_to_memory(
                role="system",
                message=f"{update_message} {extracted_statement}")

            return extracted_statement
        else:
            return None

    def add_to_db(self, entry: dict):
        """store messages to database"""
        last_message = MessagePrivate.query.filter_by(
            user_id=self.user_id,
            mediation_id=self.mediation_id,
        ).order_by(
            MessagePrivate.sequence_number.desc()).first()
        next_sequence_number = last_message.sequence_number + 1 if last_message else 1
        new_message = MessagePrivate(
            mediation_id=self.mediation_id,
            user_id=self.user_id,
            sequence_number=next_sequence_number,
            role=entry["role"],
            content=entry["content"]
        )
        # if it's a system update message, we must delete the other ones.

        db.session.add(new_message)
        db.session.commit()

class PublicMediation:
    """Handels all interations with OpenAI for Public Mediation"""
    def __init__(self, mediation_id, model="gpt-3.5-turbo"):

        self.mediation_id = mediation_id
        self.mediation_db = Mediation.query.get_or_404(mediation_id)
        self.userid_1 = self.mediation_db.initiator_id
        self.userid_2 = self.mediation_db.other_id
        self.username_1 = User.query.get_or_404(self.userid_1).username
        self.username_2 = User.query.get_or_404(self.userid_2).username
        self.initial_message_generated = False
        system_prompt = mediation_prompt.format(
            person_1=self.username_1,
            person_2=self.username_2,
            statement_1=self.mediation_db.initiator_conflict_statement,
            statement_2=self.mediation_db.other_conflict_statement,
        )
        completion_prompt = mediation_prompt_instruct.format(
            person_1=self.username_1,
            person_2=self.username_2,
        )
        agreement_prompt = evaluate_agreement_prompt.format(
            person_1=self.username_1,
            person_2=self.username_2,
        )
        self.mediator = MultiUserChatModel(
            system_prompt=system_prompt,
            instruction_prompt=completion_prompt,
            evaluate_agreement_prompt=agreement_prompt,
            model=model
        )

        messages = MessagePublic.query.filter_by(
            mediation_id=mediation_id
        ).order_by(MessagePublic.sequence_number).all()
        for message in messages:
            username = self.username_1 if message.user_id == self.userid_1 else self.username_2
            text = username + ": " + message.content if message.role == "user" else message.content
            self.mediator.add_to_memory(message=text, role=message.role, enforce_order=False)
        print(self.mediator.chat_history)
        if len(messages) != 0:
            self.initial_message_generated = True
        # track if a user needs to respond to current agreement or not
        self.to_respond_to_agreement = {self.userid_1:False, self.userid_2: False}
        self.pending_agreement = None
        self.agreed = {self.userid_1: False, self.userid_2: False}

    def send_request_to_openai(self, content, evaluate_agreement = False):
        """returns gpt response to the content given. For init it create the welcome message"""
        n_tokens = self.mediator.num_tokens_from_messages(new_user_message=content)
        if content == "init":
            self.initial_message_generated=True
        if self.mediator.model == "gpt-3.5-turbo":
            if n_tokens < 4097:
                return self.mediator(content, evaluate_agreement=evaluate_agreement)
            else:
                model = "gpt-3.5-turbo-16k"
                return self.mediator(content, model=model, evaluate_agreement=evaluate_agreement)
        else:
            if n_tokens < 8191:
                return self.mediator(content, evaluate_agreement=evaluate_agreement)
            else:
                model = "gpt-4-32k"
                return self.mediator(content, model=model, evaluate_agreement=evaluate_agreement)

    def extract_agreement(self):
        """checks if gpt generated an agreement statement, matches it and returns the
         statement"""

        pattern = r"###start_agreement###(.*?)###end_agreement###"
        last_output = self.mediator.chat_history[-1]["content"]
        match = re.search(pattern, last_output, re.DOTALL)

        if match:
            extracted_agreement = match.group(1).strip()  # Extracted conflict statement
            self.to_respond_to_agreement[self.userid_1] = True # both users must repspond
            self.to_respond_to_agreement[self.userid_2] = True
            self.pending_agreement = extracted_agreement
            return extracted_agreement
        else:
            return None

    def add_to_db(self, entry: dict, user_id=None):
        """add messages to Database"""
        last_message = MessagePublic.query.filter_by(
            mediation_id=self.mediation_id,
        ).order_by(
            MessagePublic.sequence_number.desc()).first()
        next_sequence_number = last_message.sequence_number + 1 if last_message else 1
        user_id = None if entry["role"] == "assistant" else user_id
        content = " ".join(entry["content"].split()[1:]) # don't save the username
        new_message = MessagePublic(
            mediation_id=self.mediation_id,
            user_id=user_id,
            sequence_number=next_sequence_number,
            role=entry["role"],
            content=content

        )
        db.session.add(new_message)
        db.session.commit()

    def commit_agreement(self):
        """if both users agreed, the agreement is going to be saved and stored
        in db"""
        if False in self.agreed.values(): # check if both users agreed
            return
        simple_model = SimpleCompletion()
        prompt = agreement_title_prompt.format(agreement=self.pending_agreement)
        agreement_title = simple_model(prompt)
        agreement_text = copy.copy(self.pending_agreement)
        new_agreement = Agreement(
            agreement_statement=self.pending_agreement,
            mediation_id=self.mediation_id,
            agreement_title=agreement_title
        )
        db.session.add(new_agreement)
        db.session.commit()
        for user in self.agreed:
            self.agreed[user] = False
        self.pending_agreement = None
        return agreement_title, agreement_text
