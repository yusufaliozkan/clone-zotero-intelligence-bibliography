import os
from atproto import Client
import pandas as pd
from pyzotero import zotero
import numpy as np
import requests
from typing import List, Dict
from bs4 import BeautifulSoup
from grapheme import length as grapheme_length
from datetime import datetime, timedelta
import pytz

client = Client(base_url='https://bsky.social')
bluesky_password = os.getenv("BLUESKY_PASSWORD")
client.login('intelbase.bsky.social', bluesky_password)

# Define the post content
post_content = 'Check out my profile: https://bsky.app/profile/intelbase.bsky.social'

# Define the mark_urls function (previously commented out)
def mark_urls(text):
    import re

    # Define the regex pattern for URLs
    regex = r'(https?://[^\s]+)'
    matches = re.finditer(regex, text)

    url_data = []

    # Find all matches and store their positions and URLs
    for match in matches:
        url = match.group(0)
        start = match.start()
        end = match.end()

        url_data.append({
            'start': start,
            'end': end,
            'url': url,
        })

    return url_data

# Parse URLs to get their positions
urls = mark_urls(post_content)

# Create the facets for the link
facets = []
for url in urls:
    facets.append({
        "index": {
            "byteStart": url['start'],
            "byteEnd": url['end']
        },
        "features": [
            {
                "$type": "app.bsky.richtext.facet#link",
                "uri": url['url']
            }
        ]
    })

# Send post with text and facets
post = client.send_post(
    text=post_content,
    facets=facets,
    langs=['en']
)