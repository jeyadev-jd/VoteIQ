# main.py
from firebase_functions import https_fn
from app import app as flask_app

@https_fn.on_request()
def voteiq_app(req: https_fn.Request) -> https_fn.Response:
    # This wraps the Flask app for Firebase Functions
    return flask_app(req.environ, lambda status, headers: None)
