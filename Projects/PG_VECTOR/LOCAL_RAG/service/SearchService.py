# Service Layer
import requests
import time
import logging
from cache.RedisRagCache import RedisRagCache
class SearchService:
    """Service layer to handle business logic."""
    #C:\Windows\System32\drivers\etc\hosts has localhost if used sometimes localhost not working.
    def __init__(self,cache: RedisRagCache):
        self.end_point_url='http://127.0.0.1:8080'
        self.cache = cache

    def route_embed(self,file_path,user,pwd):
        logging.info(f'::::: SERVICE LAYER >:route_embed:BEGIN:file_path:{file_path} ,user={user}')
        endPointQUery  = 'http://127.0.0.1:8080/embed'
        with open(file_path, 'rb') as file:
            file = {"file": (file_path, file)}
            data=  { "user_role":user,"password":pwd }
            result = requests.post(endPointQUery,files=file,data=data)
            response = result.json().get('message')
            if response:
                logging.debug('Controller:route_embed:::response:'+response)
        return response

    def searchQuery(self,query,search_type,user_role,pwd):
        logging.info(f'::::: SERVICE LAYER >:searchQuery::::{query} , search_type:{search_type},user_role={user_role},pwd={pwd}' )
       
        if query:
            querykey = query+'_'+search_type
            cached = self.cache.get(querykey);   
            if cached:
                result = cached["result"]
                logging.info(f"::::: RETURNED FROM REDIScache:::::::::::::::::::{result}")
                return result
            start_time = time.perf_counter()
            logging.info(f":::::::::::::::::::: DB LAYER CALL > VECTOR DB SEARCH BEGIN ::::::::::::::::::::")
            endPointQUery  = 'http://127.0.0.1:8080/query?query='+query
            result = requests.post(endPointQUery,
                                   headers={"Content-Type": "application/json"},
                                   json={'query':query,'search_type':search_type,'user_role':user_role,'pwd':pwd},
                                   timeout=(3, 30) )  #added to fix timeout issue with vector db search
            try:
                response = result.json().get('message')
            except Exception as e:
                return "No Result Found"
    
            end_time = time.perf_counter()
            time_taken = end_time - start_time
            logging.info(f":::::::::::::::::::: DB LAYER CALL > VECTOR DB SEARCH END > INFERENCE TIME TAKEN: {time_taken}::::::::::::::::::::")
            if response:
                logging.info(f"::::: SERVICE LAYER >:searchQuery::: FINAL response length={len(str(response))}")  # log the size instead of the whole response
                self.cache.set(querykey, None, response)  # or store embedding+result later
        return  response
    
    def healthCheck(self):
        endPointQUery  = 'http://127.0.0.1:8080/health_check'
        result =  requests.get(endPointQUery)
       
        return result