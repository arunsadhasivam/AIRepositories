
from langfuse import Langfuse
import os
from langfuse.callback import CallbackHandler

import logging
logging.basicConfig(level=logging.INFO)
langfuse = Langfuse()
# initialize langfuse handler once
langfuse_handler = CallbackHandler(
    secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
    public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
    host=os.getenv("LANGFUSE_BASE_URL")
)

print("::::: LANGFUSE SK::::::", os.getenv("LANGFUSE_SECRET_KEY"))
print("::::: LANGFUSE PK:::::", os.getenv("LANGFUSE_PUBLIC_KEY"))
print("::::: LANGFUSE HOST:::::", os.getenv("LANGFUSE_BASE_URL"))


class LangFuseConnector:


    def verify_langfuse(self):
        self.check = langfuse.auth_check()
        logging.info(f"::::: Langfuse auth check: {check}")
        return check