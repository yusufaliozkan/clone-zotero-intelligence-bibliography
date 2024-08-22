from atproto import Client
import pandas as pd
from pyzotero import zotero
import numpy as np
import os
import re
import requests
from typing import List, Dict
from bs4 import BeautifulSoup
from grapheme import length as grapheme_length
from datetime import datetime, timedelta
import pytz

client = Client(base_url='https://bsky.social')
bluesky_password = st.secrets["bluesky_password"]
client.login('intelbase.bsky.social', bluesky_password)

post_content = 'Check out my profile: https://bsky.app/profile/intelbase.bsky.social'
post = client.send_post(post_content)

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


# Post content
post_content = 'Check out my profile: https://bsky.app/profile/intelbase.bsky.social'

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