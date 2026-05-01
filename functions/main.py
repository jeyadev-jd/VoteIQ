# functions/main.py
from firebase_functions import https_fn
from firebase_admin import initialize_app
from app import app as flask_app

# Initialize Firebase Admin
initialize_app()

@https_fn.on_request()
def voteiq_app(req: https_fn.Request) -> https_fn.Response:
    # This allows Flask to handle the request from the Cloud Function
    # We use the app's internal __call__ which handles the WSGI interface
    with flask_app.request_context(req.environ):
        return flask_app.full_dispatch_request()

# Note: In some Firebase versions, you can simply do:
# @https_fn.on_request()
# def voteiq_app(req):
#     return flask_app(req.environ, start_response)
# But the above manual dispatch is safer for some middleware.
