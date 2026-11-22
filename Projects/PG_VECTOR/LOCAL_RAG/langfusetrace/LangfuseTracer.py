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

    #trace_event is used to log events like UI_RESPONSE_TIME and INFERENCE_TIME, which are not LLM calls but 
    # in streamlit not able to load langfuse trace_event, so we are using this method to log events.
    def trace_event(self, name, input=None, output=None, metadata=None):   # same parameters as your call
        try:                                           # tracing must never break the UI
            self.langfuse.create_event(                       # creates a trace in Langfuse v2
                name=name,                             # trace name, e.g. query-complete
                input=input,                           # shows in Input
                output=output                         # shows in Output
            )
            self.langfuse.flush()                      # send immediately
        except Exception as e:                         # swallow errors
            logging.error(f"Langfuse trace failed: {type(e).__name__}: {e}")  # log the cause

    

    # Call this when the app shuts down
    def flush(self):
        # Why: traces are sent in the background, so flush sends the remaining ones before exit
        self.langfuse.flush()