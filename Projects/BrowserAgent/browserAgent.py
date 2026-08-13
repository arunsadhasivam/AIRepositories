import os                                  # to read ANTHROPIC_API_KEY from environment
from dotenv import load_dotenv   # loads variables from .env file
load_dotenv()       
from anthropic import Anthropic            # official Anthropic Python SDK
from playwright.sync_api import sync_playwright  # controls a real browser

# Model used for the agent's decisions
MODEL = "claude-sonnet-4-6"

# Create the Anthropic client using the API key from environment variable
client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
print (os.environ.get("ANTHROPIC_API_KEY"))


class BrowserAgent:
    def __init__(self, page):
        self.page = page  # Playwright Page object - our "hands" on the browser

    # ---------- TOOL IMPLEMENTATIONS (what the agent can actually do) ----------

    def tool_navigate(self, url):
        self.page.goto(url)                     # go to the URL
        return f"Navigated to {url}"             # result sent back to Claude

    def tool_click(self, selector):
        self.page.click(selector)                # simulate a mouse click
        return f"Clicked element: {selector}"

    def tool_type(self, selector, text):
        self.page.fill(selector, text)           # fill the input field
        return f"Typed '{text}' into {selector}"

    def tool_get_page_text(self):
        text = self.page.inner_text("body")      # grab all visible text
        return text[:3000]                        # cap length so we don't blow the context window

    def execute_tool(self, name, tool_input):
        # Dispatch a tool call by name to the correct method above
        if name == "navigate":
            return self.tool_navigate(tool_input["url"])
        elif name == "click":
            return self.tool_click(tool_input["selector"])
        elif name == "type_text":
            return self.tool_type(tool_input["selector"], tool_input["text"])
        elif name == "get_page_text":
            return self.tool_get_page_text()
        else:
            return f"Unknown tool: {name}"        # safety fallback

    # ---------- TOOL DEFINITIONS (schema Claude uses to know what it can call) ----------

    def tool_definitions(self):
        return [
            {
                "name": "navigate",
                "description": "Navigate the browser to a URL",
                "input_schema": {
                    "type": "object",
                    "properties": {"url": {"type": "string"}},
                    "required": ["url"],
                },
            },
            {
                "name": "click",
                "description": "Click an element on the page using a CSS selector",
                "input_schema": {
                    "type": "object",
                    "properties": {"selector": {"type": "string"}},
                    "required": ["selector"],
                },
            },
            {
                "name": "type_text",
                "description": "Type text into an input field using a CSS selector",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "selector": {"type": "string"},
                        "text": {"type": "string"},
                    },
                    "required": ["selector", "text"],
                },
            },
            {
                "name": "get_page_text",
                "description": "Read the visible text content of the current page",
                "input_schema": {"type": "object", "properties": {}},
            },
        ]

    # ---------- AGENT LOOP ----------

    def run_task(self, task):
        # Conversation history sent to Claude on every turn
        messages = [{"role": "user", "content": task}]

        # Loop up to 10 turns to avoid runaway API costs/infinite loops
        for turn in range(10):

            response = client.messages.create(     # ask Claude what to do next
                model=MODEL,
                max_tokens=1024,
                messages=messages,
                tools=self.tool_definitions(),
            )

            # Add Claude's response to the conversation history
            messages.append({"role": "assistant", "content": response.content})

            if response.stop_reason != "tool_use":
                # Claude is done - print its final text answer and stop
                for block in response.content:
                    if block.type == "text":
                        print("FINAL ANSWER:", block.text)
                break

            # Claude wants to use one or more tools - execute each and collect results
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    print("TOOL CALL:", block.name, block.input)  # visibility while testing
                    result = self.execute_tool(block.name, block.input)  # run it via Playwright

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                    })

            # Send the tool results back as the next "user" turn
            messages.append({"role": "user", "content": tool_results})


# ---------- ENTRY POINT ----------

if __name__ == "__main__":
    with sync_playwright() as playwright:
        # Launch Chromium; headless=False so you can watch the agent work
        browser = playwright.chromium.launch(headless=False)
        page = browser.new_page()               # open a new tab

        agent = BrowserAgent(page)               # wire the agent to that tab

        # Example task - change this to whatever you want the agent to do
        agent.run_task(
            "Go to https://www.google.com, search for 'Playwright Python tutorial', "
            "and tell me the title of the first result."
        )

        browser.close()                          # clean up