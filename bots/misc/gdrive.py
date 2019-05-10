from datetime import date, timedelta
import os
import re

from google.oauth2 import service_account
from googleapiclient.discovery import build

from slackbot.bot import respond_to

from bots.utils import send_message_to_channel


SCOPES = ['https://www.googleapis.com/auth/drive']

credentials = service_account.Credentials.from_service_account_file(
    os.environ['GOOGLE_SERVICE_ACCOUNT_FILE'], scopes=SCOPES)
service = build('drive', 'v3', credentials=credentials, cache_discovery=False)


@respond_to('gdrive check', re.IGNORECASE)
def check_old_shared(message=None):
    yesterday = (date.today() - timedelta(2)).strftime("%Y-%m-%d")
    results = service.files().list(
        q=("modifiedTime > '{}' "
           "and mimeType != 'application/vnd.google-apps.folder'".format(
               yesterday)),
        pageSize=10,
        fields="nextPageToken, files(webViewLink, name)").execute()
    items = results.get('files', [])
    response = ""
    if items:
        for item in items:
            response += "* <{}|{}>\n".format(
                item['webViewLink'], item['name'])
    if response:
        response = ("Activity in legacy shared Google Drive detected! "
                    "Since yesterday:\n\n" + response)
    if message:
        if not response:
            response = "No actively in legacy shared Google Drive detected"
        message.reply(response)
    else:
        send_message_to_channel(response, '#general')