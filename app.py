from bot_config import API_BASE_URL, validate_env_variables
from gh_oauth_token import get_token, store_token, get_app_info, retrieve_app_info
from gh_utils import make_github_rest_api_call
from webhook_handlers import add_pr_comment, check_testing_done

import json
import logging
import os
import requests
import sys
import datetime
import traceback
import markdown2

from flask import Flask, request, redirect, render_template, jsonify
from objectify_json import ObjectifyJSON

log = logging.getLogger(__name__)

# Create the Flask App.
app = Flask(__name__)

pat = "4dc00e484fae8125e0a65298c9211d10efe116c4"

@app.route('/blah')
def welcome():
    """Welcome page"""
    if os.path.exists('/.env'):
        return render_template("index.html")
    else:
        # Gather required information for the manifest
        smee_url_response = requests.get('https://smee.io/new')

        # Create a new App Manifest
        app_manifest = {
            "description": "A GitHub app",
            "hook_attributes": {
                "url": smee_url_response.url
            },
            "name": "ppsvallur-test-app-6",
            "public": True,
            "redirect_url": "http://localhost:5000/setup",
            "url": "https://github.com/psvallur/python-bot-5",
            "version": "v1",
            "default_events": [
                "issues"
            ],
            "default_permissions": {
                "issues": "write",
                "metadata": "read"
            }
        }

        # return render_template("setup.html", createAppUrl='https://github.com/settings/apps/new', manifest=json.dumps(app_manifest))

        headers = {'Accept': 'application/vnd.github.fury-preview+json',
                    'Content-Type': 'application/json',
                    'Authorization': f'token {pat}'
        }
        response = requests.post('https://github.com/settings/apps/new', headers=headers, data=json.dumps({"manifest": json.dumps(app_manifest)}))
        return jsonify(response.text)


@app.route("/setup", methods=["GET"])
def authenticate():
    """Incoming Installation Request. Accept and get a new token."""
    log.info(request.headers)

    try:
        code = request.args.get('code')
        get_app_info(code)

    except Exception:
        log.error("Unable to get app info.")
        traceback.print_exc(file=sys.stderr)

    return redirect(retrieve_app_info('app_url') or 'https://github.com')


@app.route('/webhook', methods=['POST'])
def process_message():
    """
    WEBHOOK RECEIVER
    ==================
    If you have set up your webhook forwarding tool (i.e., smee) properly, webhook
    payloads from github end up being sent to your python app as POST requests
    to
        http://localhost:5000/webhook

    If you don't see expected payloads arrive here, please check the following

    - Is your github repo configured to deliver webhooks to a https://smee.io URL?
    - Is your github repo configured to deliver webhook payloads for the right EVENTS?
    - Is your webhook forwarding tool (i.e., pysmee or smee-client) running?
    - Is github SENDING webhooks to the same https://smee.io URL you're RECEIVING from?

    """
    webhook = ObjectifyJSON(request.json)
    # log.info(
    #     f'Incoming webhook [{webhook.action}]: {json.dumps(str(webhook),  sort_keys=True, indent=4)}')

    # Let's react only when a new Pull Requests has been opened.
    if request.headers['X-Github-Event'] == 'pull_request' and str(webhook.action).lower() == 'opened':
        # This webhooks has this schema - https://developer.github.com/v3/activity/events/types/#pullrequestevent
        add_pr_comment(webhook)
    if request.headers['X-Github-Event'] == 'pull_request' and str(webhook.action).lower() == 'edited':
        # This webhooks has this schema - https://developer.github.com/v3/activity/events/types/#pullrequestevent
        check_testing_done(webhook)
    else:
        log.info("Irrelavant webhook.")

    return 'GOOD'


if __name__ == 'app' or __name__ == '__main__':
    print(
        f'\n\033[96m\033[1m--- STARTING THE APP: [{datetime.datetime.now().strftime("%m/%d, %H:%M:%S")}] ---\033[0m \n')
    validate_env_variables()
    app.run()
