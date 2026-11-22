# Import the Langfuse client class and the helper that sets user and session ids
from langfuse import Langfuse, propagate_attributes
import os
import logging
logging.basicConfig(level=logging.INFO)

# Simple config: put your keys here (use your own values)
LANGFUSE_PUBLIC_KEY = os.getenv("LANGFUSE_PUBLIC_KEY")
LANGFUSE_SECRET_KEY = os.getenv("LANGFUSE_SECRET_KEY")
LANGFUSE_BASE_URL = os.getenv("LANGFUSE_BASE_URL")
os.environ["LANGFUSE_HOST"] = "http://localhost:3000"  # older name, set both to be safe


# Why: one class keeps all Langfuse code in one place, so the rest of your app only calls tracer.trace(...)
class LangfuseTracer:

    # Create the client once when the class is created
    def __init__(self):
        # Why: passing keys directly avoids any environment variable problem
        self.langfuse = Langfuse(
            public_key=LANGFUSE_PUBLIC_KEY,  # public key from the config above
            secret_key=LANGFUSE_SECRET_KEY,  # secret key from the config above
            base_url=LANGFUSE_BASE_URL,  # Langfuse server URL
        )
    
    def isAuth(self):   
        try:
            # Calls the server once to check URL and keys
            self.langfuse.auth_check()
            # Reached only if the call succeeded
            logging.info("Langfuse connected")
            return True
        except Exception as e:
            # Shows the exception type and message, which tells the cause
            logging.error(f"Langfuse failed: {type(e).__name__}: {e}")
            return False
            
    # Call this method after each LLM call to log it
    def trace(self, name, model, input, output, input_tokens=0, output_tokens=0, user_id=None, session_id=None):
        # Why: propagate_attributes (v4+) applies user and session ids to everything created inside it
        with propagate_attributes(user_id=user_id, session_id=session_id, trace_name=name):
            # Why: in v5 a generation is an observation with as_type="generation"
            with self.langfuse.start_as_current_observation(
                as_type="generation",  # marks this record as an LLM call
                name=name,  # name shown in Langfuse
                model=model,  # model name shown in the trace
                input=input,  # prompt
            ) as gen:
                # Why: output and token usage are known only after the LLM responds
                gen.update(
                    output=output,  # answer text
                    usage_details={"input": input_tokens, "output": output_tokens},  # token counts
                )

    # Call this when the app shuts down
    def flush(self):
        # Why: traces are sent in the background, so flush sends the remaining ones before exit
        self.langfuse.flush()