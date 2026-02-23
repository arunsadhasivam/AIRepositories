"""
Chat-based prompt template implementation for modern conversational models.
Supports role-based messages (system, user, assistant).
"""

from typing import List, Dict, Any, Union,Optional
from enum import Enum
from dataclasses import dataclass, field
from rag.templates import BasePromptTemplate
from rag.message.ChatMessage import ChatMessage
from rag.message.MessageRole import MessageRole
import re

import logging
logger = logging.getLogger(__name__)

class ChatPromptTemplate(BasePromptTemplate):
    """
    Production-ready chat prompt template for conversational models.
    
    Formats structured conversations with multiple messages and roles.
    Suitable for:
    - Modern chat models (GPT-4, Claude, Gemini)
    - Multi-turn conversations
    - Role-based prompting
    
    Attributes:
        messages: List of message templates
        partial_variables: Pre-filled variables
    """
    
    def __init__(self,
                 messages: List[Union[ChatMessage, Dict[str, str]]],
                 partial_variables: Optional[Dict[str, Any]] = None):
        """
        Initialize chat prompt template.
        
        Args:
            messages: List of message templates (ChatMessage or dict)
            partial_variables: Optional pre-filled variables
            
        Raises:
            ValueError: If messages are invalid
        """
        # Convert dict messages to ChatMessage objects
        self.messages = self._normalize_messages(messages)
        
        if not self.messages:
            raise ValueError("Messages list cannot be empty")
        
        # Extract all variables from all messages
        input_variables = self._extract_variables()
        
        # Remove partial variables from required inputs
        self.partial_variables = partial_variables or {}
        final_variables = [
            var for var in input_variables 
            if var not in self.partial_variables
        ]
        
        super().__init__(final_variables)
        
        logger.info(
            f"ChatPromptTemplate initialized with {len(self.messages)} messages, "
            f"{len(final_variables)} variables"
        )
    
    def _normalize_messages(self, messages: List[Union[ChatMessage, Dict[str, str]]]) -> List[ChatMessage]:
        """
        Convert message list to ChatMessage objects.
        
        Args:
            messages: List of messages (mixed types)
            
        Returns:
            List of ChatMessage objects
            
        Raises:
            ValueError: If message format is invalid
        """
        normalized = []
        
        for i, msg in enumerate(messages):
            if isinstance(msg, ChatMessage):
                normalized.append(msg)
            elif isinstance(msg, dict):
                # Convert dict to ChatMessage
                if 'role' not in msg or 'content' not in msg:
                    raise ValueError(
                        f"Message {i} must have 'role' and 'content' keys"
                    )
                
                try:
                    role = MessageRole(msg['role'])
                except ValueError:
                    raise ValueError(
                        f"Invalid role '{msg['role']}' in message {i}. "
                        f"Must be one of: {[r.value for r in MessageRole]}"
                    )
                
                normalized.append(ChatMessage(
                    role=role,
                    content=msg['content'],
                    name=msg.get('name'),
                    function_call=msg.get('function_call')
                ))
            else:
                raise ValueError(
                    f"Message {i} must be ChatMessage or dict, got {type(msg)}"
                )
        
        return normalized
    
    def _extract_variables(self) -> List[str]:
        """
        Extract all {variable} placeholders from all messages.
        
        Returns:
            List of unique variable names
        """
        variables = set()
        
        for message in self.messages:
            # Find all {variable_name} patterns in content
            found = re.findall(r'\{(\w+)\}', message.content)
            variables.update(found)
            
            # Also check name field if present
            if message.name:
                found_in_name = re.findall(r'\{(\w+)\}', message.name)
                variables.update(found_in_name)
        
        return sorted(list(variables))
    
    def format(self, **kwargs: Any) -> List[Dict[str, Any]]:
        """
        Format all messages with given variables.
        
        Args:
            **kwargs: Variable values
            
        Returns:
            List of formatted message dictionaries
            
        Raises:
            ValueError: If required variables are missing
            PromptTemplateException: If formatting fails
        """
        try:
            # Merge with partial variables
            all_values = {**self.partial_variables, **kwargs}
            
            # Validate inputs (check against non-partial variables only)
            self.validate_inputs(kwargs)
            
            # Format each message
            formatted_messages = []
            for message in self.messages:
                formatted_content = self._substitute_variables(
                    message.content, 
                    all_values
                )
                
                formatted_name = None
                if message.name:
                    formatted_name = self._substitute_variables(
                        message.name, 
                        all_values
                    )
                
                # Create formatted message
                formatted_msg = ChatMessage(
                    role=message.role,
                    content=formatted_content,
                    name=formatted_name,
                    function_call=message.function_call
                )
                
                formatted_messages.append(formatted_msg.to_dict())
            
            logger.debug(f"Formatted {len(formatted_messages)} chat messages")
            
            return formatted_messages
            
        except ValueError as ve:
            logger.error(f"Chat template formatting validation error: {str(ve)}")
            raise
        except Exception as e:
            logger.error(f"Chat template formatting failed: {str(e)}")
            raise PromptTemplateException(f"Formatting error: {str(e)}")
    
    def _substitute_variables(self, text: str, values: Dict[str, Any]) -> str:
        """
        Substitute variables in text.
        
        Args:
            text: Text with {variable} placeholders
            values: Variable values
            
        Returns:
            Text with substituted values
        """
        result = text
        
        # Replace each variable
        for key, value in values.items():
            placeholder = f"{{{key}}}"
            if placeholder in result:
                result = result.replace(placeholder, str(value))
        
        return result
    
    def format_messages(self, **kwargs: Any) -> List[ChatMessage]:
        """
        Format messages and return as ChatMessage objects.
        
        Args:
            **kwargs: Variable values
            
        Returns:
            List of formatted ChatMessage objects
        """
        formatted_dicts = self.format(**kwargs)
        return [
            ChatMessage(
                role=MessageRole(msg['role']),
                content=msg['content'],
                name=msg.get('name'),
                function_call=msg.get('function_call')
            )
            for msg in formatted_dicts
        ]
    
    @classmethod
    def from_messages(cls, 
                      messages: List[Union[tuple, Dict[str, str]]],
                      **kwargs) -> 'ChatPromptTemplate':
        """
        Create ChatPromptTemplate from simplified message format.
        
        Args:
            messages: List of (role, content) tuples or dicts
            **kwargs: Additional arguments
            
        Returns:
            ChatPromptTemplate instance
            
        Example:
            template = ChatPromptTemplate.from_messages([
                ("system", "You are a helpful {role}"),
                ("user", "{input}")
            ])
        """
        normalized = []
        
        for msg in messages:
            if isinstance(msg, tuple):
                role, content = msg
                normalized.append({"role": role, "content": content})
            elif isinstance(msg, dict):
                normalized.append(msg)
            else:
                raise ValueError(f"Invalid message format: {type(msg)}")
        
        return cls(messages=normalized, **kwargs)
    
    def add_message(self, role: Union[str, MessageRole], content: str) -> None:
        """
        Add a new message to the template.
        
        Args:
            role: Message role
            content: Message content
        """
        if isinstance(role, str):
            role = MessageRole(role)
        
        new_message = ChatMessage(role=role, content=content)
        self.messages.append(new_message)
        
        # Update input variables
        new_vars = re.findall(r'\{(\w+)\}', content)
        for var in new_vars:
            if var not in self.input_variables and var not in self.partial_variables:
                self.input_variables.append(var)
        
        logger.debug(f"Added {role.value} message to template")


# Example usage:
# template = ChatPromptTemplate.from_messages([
#     ("system", "You are a helpful assistant that translates {source_lang} to {target_lang}."),
#     ("user", "{text}")
# ])
# messages = template.format(
#     source_lang="English",
#     target_lang="Spanish",
#     text="Hello, how are you?"
# )
# Output: [
#     {"role": "system", "content": "You are a helpful assistant that translates English to Spanish."},
#     {"role": "user", "content": "Hello, how are you?"}
# ]