from elastic_search.routes import apis as search_apis
from file_handlers.routes import apis as file_handler_apis

all_routes = file_handler_apis + search_apis