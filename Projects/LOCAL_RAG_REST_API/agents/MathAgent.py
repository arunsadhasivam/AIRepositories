# math_agent.py
import re
import math
from langchain.agents import Tool, AgentExecutor, ZeroShotAgent
from langchain.chains import LLMChain
import logging
logging.basicConfig(level=logging.DEBUG)
class MathAgent:

    def __init__(self):
         # Create a tool for calculations
        logging.debug('INIT::::')
        
        
    def init():
        logging.debug('Math tool initialization :INIT()')
        math_tool = Tool(
            name="Calculator",
            func=calculator,
            description="Useful for performing mathematical calculations. Input should be a mathematical expression."
        )

    def create_math_agent(llm):
        """Create and return a math agent executor using the provided LLM."""
        logging.debug('create math Agent called:::')
        math_agent_prompt = ZeroShotAgent.create_prompt(
            [math_tool],
            prefix="You are a helpful assistant that can perform mathematical calculations. You have access to these tools:",
            suffix="Question: {input}\n{agent_scratchpad}"
        )
        
        math_agent_chain = LLMChain(llm=llm, prompt=math_agent_prompt)
        math_agent = ZeroShotAgent(llm_chain=math_agent_chain, tools=[math_tool], verbose=True)
        
        return AgentExecutor.from_agent_and_tools(
            agent=math_agent, 
            tools=[math_tool], 
            verbose=True,
            handle_parsing_errors=True
        )
    def math(query):
        return calculator(query)    

def calculator(expression: str) -> str:

    math_tool = Tool(
        name="Calculator",
        func=calculator,
        description="Useful for performing mathematical calculations. Input should be a mathematical expression."
    )
    logging.debug ('::::::::::::::calculator CALLED:::::::::::::::')
    """Evaluate a mathematical expression using Python."""
    # Sanitize input for security
    sanitized_expr = re.sub(r'[^0-9+\-*/().\s^sqrt log sin cos tan]', '', expression)
    
    # Replace math functions with Python equivalents
    sanitized_expr = sanitized_expr.replace('sqrt', 'math.sqrt')
    sanitized_expr = sanitized_expr.replace('log', 'math.log10')
    sanitized_expr = sanitized_expr.replace('sin', 'math.sin')
    sanitized_expr = sanitized_expr.replace('cos', 'math.cos')
    sanitized_expr = sanitized_expr.replace('tan', 'math.tan')
    sanitized_expr = sanitized_expr.replace('^', '**')  # Replace ^ with ** for exponentiation
    
    try:
        result = eval(sanitized_expr)
        return f"Result: {result}"
    except Exception as e:
        return f"Error in calculation: {str(e)}"

# # Create a tool for calculations
math_tool = Tool(
    name="Calculator",
    func=calculator,
    description="Useful for performing mathematical calculations. Input should be a mathematical expression."
)

    