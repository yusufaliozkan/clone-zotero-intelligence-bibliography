import os
import pandas as pd
from pyzotero import zotero
import numpy as np
import requests
from typing import List, Dict
from datetime import datetime, timedelta
import pytz
from requests_oauthlib import OAuth1

API_KEY = os.getenv('TWITTER_API_KEY')
API_SECRET = os.getenv('TWITTER_API_SECRET')
ACCESS_TOKEN = os.getenv('TWITTER_ACCESS_TOKEN')
ACCESS_TOKEN_SECRET = os.getenv('TWITTER_ACCESS_TOKEN_SECRET')


# Set up OAuth1 authentication for Twitter
auth = OAuth1(API_KEY, API_SECRET, ACCESS_TOKEN, ACCESS_TOKEN_SECRET)

# Fetching metadata from the link (keeps the same as your original)
def fetch_link_metadata(url: str) -> Dict:
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')

    title = soup.find("meta", property="og:title")
    description = soup.find("meta", property="og:description")
    image = soup.find("meta", property="og:image")

    metadata = {
        "title": title["content"] if title else "",
        "description": description["content"] if description else "",
        "image": image["content"] if image else "",
        "url": url,
    }
    return metadata

# Truncate text to fit within Twitter's 280-character limit
def truncate_title_and_construct_tweet(title: str, link: str, remaining_text: str, max_length: int) -> str:
    """Truncate the title so that the entire tweet fits within the max_length, keeping the link intact."""
    remaining_length = max_length - len(link) - len(remaining_text) - 3  # 3 for the ellipsis if title needs truncation
    truncated_title = title if len(title) <= remaining_length else title[:remaining_length] + "..."
    return f"{remaining_text}{truncated_title}\n\n{link}"

# Function to post a tweet using API v2
def post_to_twitter_v2(text: str):
    url = 'https://api.twitter.com/2/tweets'
    payload = {'text': text}

    # Make the POST request to Twitter API v2
    response = requests.post(url, json=payload, auth=auth)

    # Check if the request was successful
    if response.status_code == 201:
        print("Tweet posted successfully!")
    else:
        print(f"Failed to post tweet. Status code: {response.status_code}")
        print(response.text)

# Fetch data from Zotero (same as your original code)
library_id = '2514686'
library_type = 'group'
api_key = ''  # Optional, if your library is private

zot = zotero.Zotero(library_id, library_type)

def zotero_data(library_id, library_type):
    items = zot.top(limit=50)
    items = sorted(items, key=lambda x: x['data']['dateAdded'], reverse=True)
    data = []
    columns = ['Title', 'Publication type', 'Link to publication', 'Abstract', 'Zotero link', 'Date added', 'Date published', 'Date modified', 'Col key', 'Authors', 'Pub_venue', 'Book_title', 'Thesis_type', 'University']

    for item in items:
        creators = item['data']['creators']
        creators_str = ", ".join([
            creator.get('firstName', '') + ' ' + creator.get('lastName', '')
            if 'firstName' in creator and 'lastName' in creator
            else creator.get('name', '') 
            for creator in creators
        ])
        data.append((item['data']['title'],
                     item['data']['itemType'],
                     item['data']['url'],
                     item['data']['abstractNote'],
                     item['links']['alternate']['href'],
                     item['data']['dateAdded'],
                     item['data'].get('date'),
                     item['data']['dateModified'],
                     item['data']['collections'],
                     creators_str,
                     item['data'].get('publicationTitle'),
                     item['data'].get('bookTitle'),
                     item['data'].get('thesisType', ''),
                     item['data'].get('university', '')
                     ))
    df = pd.DataFrame(data, columns=columns)
    return df

df = zotero_data(library_id, library_type)
df['Abstract'] = df['Abstract'].replace(r'^\s*$', np.nan, regex=True)  # Replace empty string with NaN
df['Abstract'] = df['Abstract'].fillna('No abstract')

split_df= pd.DataFrame(df['Col key'].tolist())
df = pd.concat([df, split_df], axis=1)
df['Authors'] = df['Authors'].fillna('null')  

# Change type name
type_map = {
    'thesis': 'Thesis',
    'journalArticle': 'Journal article',
    'book': 'Book',
    'bookSection': 'Book chapter',
    'blogPost': 'Blog post',
    'videoRecording': 'Video',
    'podcast': 'Podcast',
    'magazineArticle': 'Magazine article',
    'webpage': 'Webpage',
    'newspaperArticle': 'Newspaper article',
    'report': 'Report',
    'forumPost': 'Forum post',
    'conferencePaper' : 'Conference paper',
    'audioRecording' : 'Podcast',
    'preprint':'Preprint',
    'document':'Document',
    'computerProgram':'Computer program',
    'dataset':'Dataset'
}

mapping_thesis_type ={
    "MA Thesis": "Master's Thesis",
    "PhD Thesis": "PhD Thesis",
    "Master Thesis": "Master's Thesis",
    "Thesis": "Master's Thesis",  # Assuming 'Thesis' refers to Master's Thesis here, adjust if necessary
    "Ph.D.": "PhD Thesis",
    "Master's Dissertation": "Master's Thesis",
    "Undergraduate Theses": "Undergraduate Thesis",
    "MPhil": "MPhil Thesis",
    "A.L.M.": "Master's Thesis",  # Assuming A.L.M. (Master of Liberal Arts) maps to Master's Thesis
    "doctoralThesis": "PhD Thesis",
    "PhD": "PhD Thesis",
    "Masters": "Master's Thesis",
    "PhD thesis": "PhD Thesis",
    "phd": "PhD Thesis",
    "doctoral": "PhD Thesis",
    "Doctoral": "PhD Thesis",
    "Master of Arts Dissertation": "Master's Thesis",
    "":'Unclassified'
}
df['Thesis_type'] = df['Thesis_type'].replace(mapping_thesis_type)
df['Publication type'] = df['Publication type'].replace(type_map)

# Ensure 'Date added' is in datetime format
df['Date added'] = pd.to_datetime(df['Date added'], errors='coerce', utc=True)

# Filter the latest publications added within the last hour
now = datetime.now(pytz.UTC)
last_hours = now - timedelta(hours=1)
df = df[df['Date added'] >= last_hours]
df = df[['Title', 'Publication type', 'Link to publication', 'Zotero link', 'Date added', 'Date published', 'Date modified', 'Authors']]

# Prepare and post items on Twitter
header = 'New addition\n\n'

for index, row in df.iterrows():
    publication_type = row['Publication type']
    title = row['Title']
    publication_date = pd.to_datetime(row['Date published'], errors='coerce').strftime('%d-%m-%Y')
    link = row['Link to publication']

    # Extract the Zotero item key from the Zotero link (last part of the URL)
    zotero_link = row['Zotero link']
    item_key = re.search(r'/items/([^/]+)$', zotero_link).group(1)  # Extracts the item key from the Zotero link

    # Fetch the Zotero item using the item key
    try:
        creators = zot.item(item_key)['data']['creators']
    except requests.exceptions.HTTPError as e:
        print(f"Error fetching item {item_key}: {e}")
        continue  # Skip this item if there's an error

    # Process author names with 'et al.' if more than two authors
    creators_str = ", ".join([
        creator.get('firstName', '') + ' ' + creator.get('lastName', '')
        if 'firstName' in creator and 'lastName' in creator
        else creator.get('name', '') 
        for creator in creators
    ])

    authors_list = creators_str.split(", ")
    if len(authors_list) > 2:
        author_name = f"{authors_list[0]} et al."
    else:
        author_name = ", ".join(authors_list)

    # The text that will remain unchanged
    remaining_text = f"{header}{publication_type}: by {author_name} (published {publication_date})\n\n"

    # Construct the post ensuring only the title is truncated
    post_text = truncate_title_and_construct_tweet(title, link, remaining_text, 280)

    # Post to Twitter
    post_to_twitter_v2(post_text)