import sys

sys.path.insert(0, 'apis/')

from app_factory import create_app
from common.routes import all_routes
# from common.db.connection import Base, engine

app = create_app()


def configure_app_routes():
    for route in all_routes:
        api_url = route[0]
        handler = route[1]
        methods = route[2]
        app.add_url_rule(
            api_url,
            '{}|{}'.format(route, handler),
            handler,
            methods=methods,
        )


configure_app_routes()


@app.route('/hello')
def hello_world():
    return 'True'


@app.route('/', methods=['GET'])
def index():
    return {'msg': 'Hello from file manager'}


if __name__ == '__main__':
    # app.run(host="0.0.0.0", port=8080)
    app.run(port=8090, debug=True)
