import os
import logging
import requests
logging.basicConfig(level=logging.DEBUG)
import logging
logging.basicConfig(level=logging.DEBUG)
from service.SearchService import SearchService
class SearchController:    
  
    def __init__(self,service:SearchService):
        self.end_point_url='http://localhost:8080'
        self.service=SearchService
  
        
    def route_embed(self,file_path):
        logging.debug('Controller:route_embed:::'+file_path )
        return  self.service.route_embed(file_path)

    def searchQuery(self,query,type):
        logging.debug('Controller:searchQuery:::'+query )
        return  self.service.searchQuery(query,type)
       

    # def route_delete():
    #     db = get_vector_db()
    #     db.delete_collection()

    #     return jsonify({"message": "Collection deleted successfully"}), 200

# if __name__ == '__main__':
#     app.run(host="0.0.0.0", port=8080, debug=True)

