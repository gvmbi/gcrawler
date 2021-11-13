import datetime
import logging
import os
import requests
from bs4 import BeautifulSoup
import telebot
from azure.storage.blob import BlobClient
import hashlib

import azure.functions as func


def hash_string(input_string: str) -> str:
    return hashlib.sha256(input_string.encode("utf-8")).hexdigest()


def main(mytimer: func.TimerRequest) -> None:
    utc_timestamp = datetime.datetime.utcnow().replace(
        tzinfo=datetime.timezone.utc).isoformat()

    if mytimer.past_due:
        logging.info('The timer is past due!')

    logging.info('Python timer trigger function ran at %s', utc_timestamp)

    url = os.environ['TargetUrl']
    search_term = os.environ['SearchTerm']
    reqs = requests.get(url)
    soup = BeautifulSoup(reqs.text, 'html.parser')
    token = telebot.TeleBot(os.environ['TelebotToken'])
    chat_id = os.environ['TelebotChatId']

    urls = []
    for link in soup.find_all('a'):
        link_url = link.get('href')
        # Add only links that contain the search term
        if search_term in link_url:
            urls.append(link_url)

    logging.info(f"Looking for: {search_term}")
    logging.info(f"Urls conatining the pattern: {urls}")

    lst_to_str = ';'.join([str(i) for i in urls])
    new_hash = hash_string(lst_to_str)
    now = datetime.datetime.now()
    file_suffix = now.strftime("%Y%m%d%I%M%S")
    year = now.year
    month = now.month
    day = now.day

    blob = BlobClient.from_connection_string(
        conn_str=os.environ['AzureWebJobsStorage'], container_name="hashstore", blob_name=f'urls/{year}/{month}/{day}/html-{file_suffix}.html')
    blob.upload_blob(lst_to_str, blob_type='BlockBlob')

    logging.info(new_hash)

    blob = BlobClient.from_connection_string(
        conn_str=os.environ['AzureWebJobsStorage'], container_name="hashstore", blob_name='hash.tmp')
    blob_hash = ''
    if blob.exists():
        blob_hash = str(blob.download_blob().readall())
        if blob_hash != new_hash:
            message = f'Hash of this page: {url} has changed'
            bot = telebot.TeleBot(token)
            bot.config['api_key'] = token
            bot.send_message(chat_id, message)
            blob.delete_blob()

    blob.upload_blob(new_hash, blob_type='BlockBlob')

    logging.info(f'Old hash >>>> {blob_hash}')
    logging.info(f'New hash >>>> {new_hash}')
