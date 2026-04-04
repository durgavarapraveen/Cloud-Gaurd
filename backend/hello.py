from flask import Blueprint

hello_app = Blueprint("hello_app", __name__)

@hello_app.route("/hello")
def helloWorldFunction():
    return "<p>Hello from hello route!</p>"