"""
Router chain for conditional execution paths.
Selects appropriate chain based on input characteristics.
"""

from typing import Dict, Any, Callable, Optional


from typing import Dict, Any, Optional, List
from rag.chain.BaseChain import BaseChain
from rag.exception.ChainException import ChainException
import logging
logger = logging.getLogger(__name__)


class RouterChain(BaseChain):
    """
    Production-ready router chain for conditional logic.
    
    Routes inputs to different chains based on routing logic.
    
    Suitable for:
    - Conditional workflows
    - Multi-domain applications
    - Intent-based routing
    
    Attributes:
        router_func: Function to determine which chain to use
        chains: Dictionary mapping route names to chains
        default_chain: Fallback chain if no route matches
    """
    
    def __init__(self,
                 router_func: Callable[[Dict[str, Any]], str],
                 chains: Dict[str, BaseChain],
                 default_chain: Optional[BaseChain] = None,
                 verbose: bool = False):
        """
        Initialize router chain.
        
        Args:
            router_func: Function that returns route name given inputs
            chains: Dictionary of route_name -> chain
            default_chain: Chain to use if route not found
            verbose: Enable detailed logging
            
        Raises:
            ValueError: If configuration is invalid
        """
        super().__init__(name="RouterChain", verbose=verbose)
        
        if not chains:
            raise ValueError("Chains dictionary cannot be empty")
        if router_func is None:
            raise ValueError("Router function cannot be None")
        
        self.router_func = router_func
        self.chains = chains
        self.default_chain = default_chain
        
        logger.info(f"RouterChain initialized with {len(chains)} routes")
    
    def run(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Route input to appropriate chain and execute.
        
        Args:
            inputs: Input dictionary
            
        Returns:
            Output from selected chain
            
        Raises:
            ChainException: If routing or execution fails
        """
        try:
            # Step 1: Determine route
            route_name = self._determine_route(inputs)
            
            if self.verbose:
                logger.info(f"Routed to: {route_name}")
            
            # Step 2: Get appropriate chain
            selected_chain = self._get_chain(route_name)
            
            if selected_chain is None:
                raise ChainException(f"No chain found for route '{route_name}'")
            
            # Step 3: Execute selected chain
            result = selected_chain.run(inputs)
            
            # Add routing metadata to result
            result['_route'] = route_name
            result['_chain'] = selected_chain.name
            
            return result
            
        except Exception as e:
            logger.error(f"RouterChain execution failed: {str(e)}")
            raise ChainException(f"Router chain error: {str(e)}")
    
    def _determine_route(self, inputs: Dict[str, Any]) -> str:
        """
        Determine which route to use based on inputs.
        
        Args:
            inputs: Input dictionary
            
        Returns:
            Route name
            
        Raises:
            ChainException: If router function fails
        """
        try:
            route = self.router_func(inputs)
            
            if not isinstance(route, str):
                raise ValueError(f"Router function must return string, got {type(route)}")
            
            return route
            
        except Exception as e:
            logger.error(f"Routing failed: {str(e)}")
            raise ChainException(f"Routing error: {str(e)}")
    
    def _get_chain(self, route_name: str) -> Optional[BaseChain]:
        """
        Get chain for given route.
        
        Args:
            route_name: Name of the route
            
        Returns:
            Chain instance or None if not found
        """
        chain = self.chains.get(route_name)
        
        if chain is None and self.default_chain is not None:
            logger.info(f"Route '{route_name}' not found, using default chain")
            return self.default_chain
        
        return chain
    
    def add_route(self, route_name: str, chain: BaseChain) -> None:
        """
        Add a new route to the router.
        
        Args:
            route_name: Name of the route
            chain: Chain to execute for this route
        """
        self.chains[route_name] = chain
        logger.info(f"Added route: {route_name}")
    
    def remove_route(self, route_name: str) -> None:
        """
        Remove a route from the router.
        
        Args:
            route_name: Name of the route to remove
        """
        if route_name in self.chains:
            del self.chains[route_name]
            logger.info(f"Removed route: {route_name}")


# Example usage:
# def intent_router(inputs: Dict[str, Any]) -> str:
#     """Route based on detected intent."""
#     text = inputs.get('text', '').lower()
#     
#     if 'weather' in text:
#         return 'weather'
#     elif 'translate' in text:
#         return 'translation'
#     else:
#         return 'general'
# 
# weather_chain = LLMChain(llm=llm, prompt_template=weather_template)
# translation_chain = LLMChain(llm=llm, prompt_template=translation_template)
# general_chain = LLMChain(llm=llm, prompt_template=general_template)
# 
# router = RouterChain(
#     router_func=intent_router,
#     chains={
#         'weather': weather_chain,
#         'translation': translation_chain,
#         'general': general_chain
#     }
# )
# 
# result = router.run({"text": "What's the weather like?"})
# # Routes to weather_chain