import os
from os.path import abspath, dirname, join

APPLICATION_ROOT = dirname(dirname(abspath(__file__)))

DB_PATH = os.environ.get("DB_PATH", join(APPLICATION_ROOT, "ebmbot.db"))
WORKSPACE_DIR = os.environ.get("WORKSPACE_DIR", join(APPLICATION_ROOT, "workspace"))
LOGS_DIR = os.environ["LOGS_DIR"]
SLACK_LOGS_CHANNEL = os.environ["SLACK_LOGS_CHANNEL"]

# "Bot User OAuth Access Token" from https://api.slack.com/apps/A6B85C8KC/oauth
SLACKBOT_API_TOKEN = os.environ["SLACKBOT_API_TOKEN"]

# "Secret" from https://github.com/ebmdatalab/openprescribing/settings/hooks/85994427
GITHUB_WEBHOOK_SECRET = os.environ["GITHUB_WEBHOOK_SECRET"].encode("ascii")

# From "Payload URL" from https://github.com/ebmdatalab/openprescribing/settings/hooks/85994427
GITHUB_WEBHOOK_PORT = int(os.environ["GITHUB_WEBHOOK_PORT"])
