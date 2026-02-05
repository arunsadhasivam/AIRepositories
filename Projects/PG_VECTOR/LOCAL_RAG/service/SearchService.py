# Service Layer
import requests
import logging
logging.basicConfig(level=logging.DEBUG)
from cache.RedisRagCache import RedisRagCache
class SearchService:
    """Service layer to handle business logic."""
    def __init__(self,cache: RedisRagCache):
        self.end_point_url='http://localhost:8080'
        self.cache = cache

    def route_embed(self,file_path):
        logging.debug('SearchService:route_embed:BEGIN:file_path:'+file_path)
        endPointQUery  = 'http://localhost:8080/embed'
        with open(file_path, 'rb') as file:
            files = {"file": (file_path, file)}
            result = requests.post(endPointQUery,files=files)
            response = result.json().get('message')
            if response:
                logging.debug('Controller:route_embed:::response:'+response)
        return response

    def searchQuery(self,query,type):
        logging.debug('SearchService:searchQuery:::'+query )
        if query:
            cached = self.cache.get(query);   
            if cached:
                result = cached["result"]
                print(":::RETURNED FROM REDIScache:::::::::::::::::::",result)
                return result
        
            endPointQUery  = 'http://localhost:8080/query?query='+query
            result = requests.post(endPointQUery,headers={"Content-Type": "application/json"},json={'query':query})
            response = result.json().get('message')
            logging.debug('Controller:response:::'+response)
            self.cache.set(query, None, response)  # or store embedding+result later
        return  response
    
    