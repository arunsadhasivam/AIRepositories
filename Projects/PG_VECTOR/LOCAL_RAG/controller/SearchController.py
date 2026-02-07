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

    def searchQuery(self,query,type):
        logging.info('::::: SEARCH CONTROLLER:searchQuery:::'+query )
        return  self.service.searchQuery(query,type)
       
 
    # def route_delete():
    #     db = get_vector_db()
    #     db.delete_collection()

    #     return jsonify({"message": "Collection deleted successfully"}), 200

# if __name__ == '__main__':
#     app.run(host="0.0.0.0", port=8080, debug=True)

