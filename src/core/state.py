from typing import Annotated, Sequence, TypedDict
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from langchain.agents.middleware.types import AgentMiddleware

def clean_messages_reducer(left: Sequence[BaseMessage], right: Sequence[BaseMessage]) -> Sequence[BaseMessage]:
    """
    Reducer function to merge messages while stripping ephemeral 
    metadata (like 'assembling_tool') from the history before persistence.
    """
    updated_messages = add_messages(left, right)
    
    cleaned_messages = []
    for msg in updated_messages:
        new_msg = msg.copy()
        if hasattr(new_msg, 'additional_kwargs') and new_msg.additional_kwargs:
            new_msg.additional_kwargs.pop('assembling_tool', None)
            new_msg.additional_kwargs.pop('is_finished', None)
        cleaned_messages.append(new_msg)
        
    return cleaned_messages

class AgentState(TypedDict):
    """Generic state schema for the Agentic OS."""
    messages: Annotated[Sequence[BaseMessage], clean_messages_reducer]

class CleanKwargsMiddleware(AgentMiddleware):
    """
    Sanitization Middleware to strip ephemeral metadata from messages 
    before they are stored in persistence.
    """
    def before_store(self, messages):
        sanitized_messages = []
        for msg in messages:
            if hasattr(msg, 'additional_kwargs') and msg.additional_kwargs:
                new_msg = msg.copy()
                new_msg.additional_kwargs.pop('assembling_tool', None)
                sanitized_messages.append(new_msg)
            else:
                sanitized_messages.append(msg)
        return sanitized_messages