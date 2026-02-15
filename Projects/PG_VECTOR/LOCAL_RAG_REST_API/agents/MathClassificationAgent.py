# math_agent.py
import re
import math
from langchain.agents import Tool, AgentExecutor, create_react_agent
from langchain import hub
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)


def calculator(expression: str) -> str:
    """
    Evaluate a mathematical expression using Python.
    
    Args:
        expression (str): Mathematical expression to evaluate
        
    Returns:
        str: Result of calculation or error message
    """
    try:
        # Log calculator function called
        logging.debug('::::::::::::::calculator CALLED:::::::::::::::')
        # Log original expression
        logging.debug(f'Original expression: {expression}')
        
        # Start with original expression
        sanitized_expr = expression
        
        # Replace math functions with Python equivalents FIRST (before sanitizing)
        sanitized_expr = sanitized_expr.replace('sqrt', 'math.sqrt')
        sanitized_expr = sanitized_expr.replace('log', 'math.log10')
        sanitized_expr = sanitized_expr.replace('sin', 'math.sin')
        sanitized_expr = sanitized_expr.replace('cos', 'math.cos')
        sanitized_expr = sanitized_expr.replace('tan', 'math.tan')
        sanitized_expr = sanitized_expr.replace('^', '**')  # Replace ^ with ** for exponentiation
        
        # Log after function replacement
        logging.debug(f'After function replacement: {sanitized_expr}')
        
        # Now sanitize - allow only safe characters including 'math.' prefix
        sanitized_expr = re.sub(r'[^0-9+\-*/().\smath]', '', sanitized_expr)
        
        # Log final sanitized expression
        logging.debug(f'Final expression to eval: {sanitized_expr}')
        
        # Evaluate the sanitized expression in a restricted namespace for security
        result = eval(sanitized_expr, {"__builtins__": {}}, {"math": math})
        
        # Log result - convert to string for logging
        logging.debug(f"::::: Math Function Called : Response :::::{result}")
        
        # Return result as string
        return f"Result: {result}"
        
    except Exception as e:
        # Log error with full details
        logging.error(f"Error in calculation for expression '{expression}': {str(e)}")
        # Return error message
        return f"Error in calculation: {str(e)}"


# Create the math tool OUTSIDE any class/function - defined at module level
math_tool = Tool(
    name="Calculator",
    func=calculator,
    description="Useful for performing mathematical calculations. Input should be a mathematical expression."
)


class MathClassificationAgent:
    """
    Agent for handling mathematical calculations.
    """
    
    def __init__(self):
        """
        Initialize MathClassificationAgent.
        """
        # Log initialization
        logging.debug('INIT::::')
        # Initialize requires_math flag
        self.requires_math = False
    
    @staticmethod
    def init():
        """
        Initialize math tool.
        """
        # Log math tool initialization
        logging.debug('Math tool initialization :INIT()')
        # Note: math_tool is already defined at module level
    
    @staticmethod
    def create_math_agent(llm):
        """
        Create and return a math agent executor using the provided LLM.
        Uses create_react_agent (replaces deprecated ZeroShotAgent).
        
        Args:
            llm: Language model to use for the agent
            
        Returns:
            AgentExecutor: Configured math agent executor
        """
        # Log agent creation
        logging.debug('::::: create math Agent called :::::')
        
        try:
            # Pull the react prompt from LangChain hub
            prompt = hub.pull("hwchase17/react")
            
        except Exception as e:
            # If hub pull fails, create custom prompt
            logging.warning(f'Failed to pull prompt from hub: {e}, using custom prompt')
            
            from langchain.prompts import PromptTemplate
            
            # Create custom react-style prompt template
            template = """Answer the following questions as best you can. You have access to the following tools:

{tools}

Use the following format:

Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question

Begin!

Question: {input}
Thought:{agent_scratchpad}"""

            # Create prompt template
            prompt = PromptTemplate(
                template=template,
                input_variables=["input", "agent_scratchpad"],
                partial_variables={
                    "tools": "Calculator: Useful for performing mathematical calculations. Input should be a mathematical expression.",
                    "tool_names": "Calculator"
                }
            )
        
        # Create react agent with LLM, tools, and prompt
        agent = create_react_agent(
            llm=llm,
            tools=[math_tool],
            prompt=prompt
        )
        
        # Create and return agent executor
        return AgentExecutor(
            agent=agent,
            tools=[math_tool],
            verbose=True,
            handle_parsing_errors=True,
            max_iterations=3  # Limit iterations to prevent infinite loops
        )
    
    @staticmethod
    def math(query):
        """
        Perform mathematical calculation on the query.
        
        Args:
            query (str): Mathematical expression to evaluate
            
        Returns:
            str: Result of calculation
        """
        # Call calculator function with query
        return calculator(query)