"""
Entity-tracking memory for context-aware conversations.
Tracks important entities (people, places, things) across conversation.
"""

import logging
from rag.memory.BaseMemory import BaseMemory
from typing import Optional,Dict,Any
from rag.exception import MemoryException
from rag.memory import ConversationTurn
from rag.chain import LLMProtocol
import threading
logger = logging.getLogger(__name__)

class ConversationEntityMemory(BaseMemory):
    """
    Production-ready entity-tracking memory.
    
    Extracts and tracks entities mentioned in conversation.
    
    Features:
    - Automatic entity extraction
    - Entity fact accumulation
    - Contextual entity recall
    
    Suitable for:
    - Customer service (track customer info)
    - Personal assistants (remember user preferences)
    - Multi-entity conversations
    
    Attributes:
        llm: Language model for entity extraction
        entities: Dictionary of entity_name -> facts
        chat_history: Recent conversation buffer
    """
    
    def __init__(self,
                 llm: LLMProtocol,
                 memory_key: str = "history",
                 input_key: str = "input",
                 output_key: str = "output",
                 entity_extraction_prompt: Optional[str] = None,
                 k: int = 3):
        """
        Initialize entity memory.
        
        Args:
            llm: Language model for entity extraction
            memory_key: Key for memory in context
            input_key: Key for user input
            output_key: Key for AI output
            entity_extraction_prompt: Custom prompt for extraction
            k: Number of recent turns to keep
            
        Raises:
            ValueError: If llm is None
        """
        super().__init__(memory_key, input_key, output_key)
        
        if llm is None:
            raise ValueError("LLM cannot be None")
        
        self.llm = llm
        self.k = k
        
        # Default entity extraction prompt
        self.entity_extraction_prompt = entity_extraction_prompt or """Extract entities (people, places, organizations, products, etc.) and their attributes from this conversation.

User: {user_input}
Assistant: {ai_output}

Return entities as JSON: {{"entity_name": "key facts about entity", ...}}
Entities:"""
        
        from collections import deque
        self.entities: Dict[str, List[str]] = {}  # entity -> list of facts
        self.chat_history: deque = deque(maxlen=k)
        self._lock = threading.Lock()
        
        logger.info(f"ConversationEntityMemory initialized: k={k}")
    
    def save_context(self, inputs: Dict[str, Any], outputs: Dict[str, Any]) -> None:
        """
        Save conversation and extract entities.
        
        Args:
            inputs: User input dictionary
            outputs: AI output dictionary
            
        Raises:
            MemoryException: If save fails
        """
        try:
            user_message = self._extract_input(inputs)
            ai_message = self._extract_output(outputs)
            
            turn = ConversationTurn(
                user_message=user_message,
                ai_message=ai_message
            )
            
            with self._lock:
                # Save to history buffer
                self.chat_history.append(turn)
                
                # Extract entities from this turn
                self._extract_entities(user_message, ai_message)
            
            logger.debug(f"Saved turn and extracted entities (total entities: {len(self.entities)})")
            
        except ValueError as ve:
            logger.error(f"Failed to save context: {str(ve)}")
            raise MemoryException(f"Save failed: {str(ve)}")
        except Exception as e:
            logger.error(f"Unexpected error saving context: {str(e)}")
            raise MemoryException(f"Save error: {str(e)}")
    
    def _extract_entities(self, user_input: str, ai_output: str) -> None:
        """
        Extract entities from conversation turn using LLM.
        
        Args:
            user_input: User message
            ai_output: AI response
        """
        try:
            # Format extraction prompt
            prompt = self.entity_extraction_prompt.format(
                user_input=user_input,
                ai_output=ai_output
            )
            
            # Call LLM to extract entities
            response = self.llm.generate(prompt)
            
            # Parse JSON response
            try:
                import json
                entities_dict = json.loads(response)
                
                # Update entity knowledge base
                for entity_name, facts in entities_dict.items():
                    if entity_name not in self.entities:
                        self.entities[entity_name] = []
                    
                    # Add new facts (avoid duplicates)
                    if isinstance(facts, str):
                        if facts not in self.entities[entity_name]:
                            self.entities[entity_name].append(facts)
                    elif isinstance(facts, list):
                        for fact in facts:
                            if fact not in self.entities[entity_name]:
                                self.entities[entity_name].append(fact)
                
                logger.debug(f"Extracted {len(entities_dict)} entities")
                
            except json.JSONDecodeError:
                logger.warning("Failed to parse entity extraction JSON")
            
        except Exception as e:
            logger.error(f"Entity extraction failed: {str(e)}")
            # Don't raise - continue without entity extraction
    
    def load_memory_variables(self, inputs: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Load entity knowledge and recent conversation.
        
        Args:
            inputs: Optional input context (not used)
            
        Returns:
            Dictionary with entity context and recent messages
        """
        try:
            with self._lock:
                parts = []
                
                # Add entity knowledge
                if self.entities:
                    entity_context = "Known entities:\n"
                    for entity_name, facts in self.entities.items():
                        facts_str = "; ".join(facts)
                        entity_context += f"- {entity_name}: {facts_str}\n"
                    parts.append(entity_context)
                
                # Add recent conversation
                if self.chat_history:
                    recent_parts = []
                    for turn in self.chat_history:
                        recent_parts.append(f"User: {turn.user_message}")
                        recent_parts.append(f"Assistant: {turn.ai_message}")
                    parts.append(f"Recent conversation:\n" + "\n".join(recent_parts))
                
                full_context = "\n\n".join(parts) if parts else ""
                
                return {self.memory_key: full_context}
                
        except Exception as e:
            logger.error(f"Failed to load memory: {str(e)}")
            raise MemoryException(f"Load error: {str(e)}")
    
    def clear(self) -> None:
        """Clear all memory including entities."""
        with self._lock:
            self.entities.clear()
            self.chat_history.clear()
        logger.info("Cleared entity memory")
    
    def get_entities(self) -> Dict[str, List[str]]:
        """Get all tracked entities."""
        with self._lock:
            return self.entities.copy()
    
    def get_entity_facts(self, entity_name: str) -> Optional[List[str]]:
        """
        Get facts about a specific entity.
        
        Args:
            entity_name: Name of the entity
            
        Returns:
            List of facts or None if entity not found
        """
        with self._lock:
            return self.entities.get(entity_name)


# Example usage:
# llm = OpenAI(api_key="...")
# memory = ConversationEntityMemory(llm=llm, k=3)
# 
# # Conversation 1
# memory.save_context(
#     inputs={"input": "My name is John and I work at Google"},
#     outputs={"output": "Nice to meet you John!"}
# )
# 
# # Conversation 2
# memory.save_context(
#     inputs={"input": "What do you know about me?"},
#     outputs={"output": "You're John and you work at Google"}
# )
# 
# # Load context
# context = memory.load_memory_variables()
# print(context["history"])
# # Output includes:
# # Known entities:
# # - John: name is John, works at Google
# # - Google: company where John works