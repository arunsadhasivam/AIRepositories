# Service Layer
import requests
import logging
logging.basicConfig(level=logging.DEBUG)

class SearchService:
    """Service layer to handle business logic."""
    def __init__(self):
        self.end_point_url='http://localhost:8080'

    def route_embed(file_path):
        logging.debug('SearchService:route_embed:BEGIN:file_path:'+file_path)
        endPointQUery  = 'http://localhost:8080/embed'
        with open(file_path, 'rb') as file:
            files = {"file": (file_path, file)}
            result = requests.post(endPointQUery,files=files)
            response = result.json().get('message')
            if response:
                logging.debug('Controller:route_embed:::response:'+response)
        return response

    def searchQuery(query,type):
        logging.debug('SearchService:searchQuery:::'+query )
        if query:
            endPointQUery  = 'http://localhost:8080/query?query='+query
            result = requests.post(endPointQUery,headers={"Content-Type": "application/json"},json={'query':query})
            response = result.json().get('message')
            logging.debug('Controller:response:::'+response)
        return  response