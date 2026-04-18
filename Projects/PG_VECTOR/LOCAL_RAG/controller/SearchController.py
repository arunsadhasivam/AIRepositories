import os
import logging
import requests
from cache.RedisRagCache import RedisRagCache
import logging
from service.SearchService import SearchService

class SearchController:    
  
    def __init__(self,service:SearchService):
        self.end_point_url='http://localhost:8080'
        self.service=service
        
    def route_embed(self,file_path,user_role,pwd):
        logging.info('::::: SEARCH CONTROLLER:route_embed:::'+file_path  )
        return  self.service.route_embed(file_path,user_role,pwd)

    def searchQuery(self,query,search_type,user_role,pwd):
        logging.info(f'::::: SEARCH CONTROLLER:searchQuery:::{query} , search_type:{search_type},user_role={user_role},pwd={pwd}' )
    
        return  self.service.searchQuery(query,search_type,user_role,pwd)
    def healthCheck(self):
        logging.info('::::: HEALTH CHECK:::::' )
        return  self.service.healthCheck()
       