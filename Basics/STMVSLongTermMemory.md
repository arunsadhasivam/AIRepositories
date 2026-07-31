



Short-Term Memory (Context Window)
==================================
It is the working memory the model uses during a single call. The system prompt, conversation history, tool outputs, and retrieved content are placed into the context window so the model can reason over them and generate a response.

But once the call ends, that window resets. As the conversation grows longer, the model may also lose track of earlier details inside the same window.

Long-Term Memory (External Storage)
====================================

LTM lives outside the model and persists across sessions. In practice, it often shows up as episodic memory for past interactions, 
semantic memory for facts and preferences, and procedural memory for rules or workflows.

When a new call starts, the agent retrieves relevant memory records from the LTM store and injects them into the context window through RAG so the model can reason over them. After a session ends, key information can be extracted and written back to LTM storage for future use. 

In production, LTM does not replace the context window. It feeds it. Even a 1M token window resets after every call. For isolated single-call
tasks STM is enough. Agents that need to remember users, past decisions, and outcomes across sessions need both.


<img width="800" height="967" alt="image" src="https://github.com/user-attachments/assets/93160281-1dac-4542-b461-711b03f40d25" />
