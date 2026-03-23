# Service Layer
import requests
import logging
from cache.RedisRagCache import RedisRagCache
class SearchService:
    """Service layer to handle business logic."""
    def __init__(self,cache: RedisRagCache):
        self.end_point_url='http://localhost:8080'
        self.cache = cache

    def route_embed(self,file_path,user,pwd):
        logging.info(f'::::: SEARCHSERVICE:route_embed:BEGIN:file_path:{file_path} ,user={user}')
        endPointQUery  = 'http://localhost:8080/embed'
        with open(file_path, 'rb') as file:
            file = {"file": (file_path, file)}
            data=  { "user_role":user,"password":pwd }
            result = requests.post(endPointQUery,files=file,data=data)
            response = result.json().get('message')
            if response:
                logging.debug('Controller:route_embed:::response:'+response)
        return response

    def searchQuery(self,query,search_type,user_role,pwd):
        logging.info(f'::::: SEARCHSERVICE:searchQuery::::{query} , search_type:{search_type},user_role={user_role},pwd={pwd}' )
       
        if query:
            querykey = query+'_'+search_type
            cached = self.cache.get(querykey);   
            if cached:
                result = cached["result"]
                logging.info(f"::::: RETURNED FROM REDIScache:::::::::::::::::::{result}")
                return result
        
            endPointQUery  = 'http://localhost:8080/query?query='+query
            result = requests.post(endPointQUery,headers={"Content-Type": "application/json"},json={'query':query,'search_type':search_type,'user_role':user_role,'pwd':pwd})
            try:
                response = result.json().get('message')
            except Exception as e:
                return "No Result Found"
            
            if response:
                logging.info(f'::::: Controller:response:::{response}')
                self.cache.set(querykey, None, response)  # or store embedding+result later
        return  response
    
    