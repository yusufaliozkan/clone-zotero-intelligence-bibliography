from pyzotero import zotero
import os
# import tweepy as tw
import pandas as pd
import datetime
import json, sys
from datetime import date, timedelta  
import datetime
import plotly.express as px
import pycountry
import re
import pandas as pd
import requests
import time
from datetime import datetime, timedelta

## RETRIEVING CITATION COUNTS AND OPEN ACCESS STATUSES FROM OPENALEX

df_doi = pd.read_csv('all_items.csv')

df_doi = df_doi[['Zotero link', 'DOI']].dropna()
df_doi = df_doi.drop(df_doi[df_doi['DOI'] == ''].index)
df_doi = df_doi.reset_index(drop=True)
df_doi['DOI'] = df_doi['DOI'].str.replace('https://doi.org/', '')

def fetch_article_metadata(doi):
    base_url = 'https://api.openalex.org/works/https://doi.org/'
    response = requests.get(base_url + doi)
    if response.status_code == 200:
        data = response.json()
        counts_by_year = data.get('counts_by_year', [])
        if counts_by_year:
            first_citation_year = min(entry.get('year') for entry in data['counts_by_year'])
        else:
            first_citation_year = None
        if data.get('counts_by_year'):
            last_citation_year = max(entry.get('year') for entry in data['counts_by_year'])
        else:
            last_citation_year = None

        article_metadata = {
            'ID': data.get('id'),
            'Citation': data.get('cited_by_count'),
            'OA status': data.get('open_access', {}).get('is_oa'),
            'Citation_list': data.get('cited_by_api_url'),
            'First_citation_year': first_citation_year,
            'Last_citation_year': last_citation_year,
            'Publication_year': data.get('publication_year'),
            'OA_link': data.get('open_access', {}).get('oa_url')
        }
        return article_metadata
    else:
        return {
            'ID': None,
            'Citation': None,
            'OA status': None,
            'First_citation_year': None,
            'Last_citation_year': None,
            'Publication_year': None,
            'OA_link': None
        }

df_doi['ID'] = None
df_doi['Citation'] = None
df_doi['OA status'] = None
df_doi['Citation_list'] = None
df_doi['First_citation_year'] = None
df_doi['Last_citation_year'] = None
df_doi['Publication_year'] = None
df_doi['OA_link'] = None

# Iterate over each row in the DataFrame
for index, row in df_doi.iterrows():
    doi = row['DOI']
    article_metadata = fetch_article_metadata(doi)
    if article_metadata:
        # Update DataFrame with fetched information
        df_doi.at[index, 'ID'] = article_metadata['ID']
        df_doi.at[index, 'Citation'] = article_metadata['Citation']
        df_doi.at[index, 'OA status'] = article_metadata['OA status']
        df_doi.at[index, 'First_citation_year'] = article_metadata['First_citation_year']
        df_doi.at[index, 'Last_citation_year'] = article_metadata['Last_citation_year']
        df_doi.at[index, 'Citation_list'] = article_metadata.get('Citation_list', None)
        df_doi.at[index, 'Publication_year'] = article_metadata['Publication_year']
        df_doi.at[index, 'OA_link'] = article_metadata.get('OA_link', None)

# Calculate the difference between First_citation_year and Publication_year
df_doi['Year_difference'] = df_doi['First_citation_year'] - df_doi['Publication_year']
df_doi.to_csv('citations.csv')

df_doi_2 = pd.read_csv('citations.csv', usecols=lambda column: column != 'Unnamed: 0')

df_1 = pd.read_csv('all_items.csv', usecols=lambda column: column != 'Unnamed: 0')
df_doi_1 = pd.read_csv('citations.csv', usecols=lambda column: column != 'Unnamed: 0')
df_doi_1 = df_doi_1.drop(columns=['DOI'])
df_1 = pd.merge(df_1, df_doi_1, on='Zotero link', how='left')
df_1.to_csv('all_items.csv')

df_2 = pd.read_csv('all_items_duplicated.csv', usecols=lambda column: column != 'Unnamed: 0')
df_doi_2 = pd.read_csv('citations.csv', usecols=lambda column: column != 'Unnamed: 0')
df_doi_2 = df_doi_2.drop(columns=['DOI'])
df_2 = pd.merge(df_2, df_doi_2, on='Zotero link', how='left')
df_2.to_csv('all_items_duplicated.csv')


## ZOTERO CITATION FORMATS

df_zotero_id = pd.read_csv('zotero_citation_format.csv')
df_all = pd.read_csv('all_items.csv')
df_all = df_all[['Zotero link']]
df_all['zotero_item_key'] = df_all['Zotero link'].str.replace('https://www.zotero.org/groups/intelligence_bibliography/items/', '')
df_all = df_all.drop_duplicates()
df_not_zotero_id = df_all[~df_all['zotero_item_key'].isin(df_zotero_id['zotero_item_key'])]
df_not_zotero_id = df_not_zotero_id[['zotero_item_key']].reset_index(drop=True)

user_id = '2514686'

# Base URL for Zotero API
base_url = 'https://api.zotero.org'

# Initialize an empty string to accumulate bibliographies
all_bibliographies = ""

# List to store bibliographies 
bibliographies = []

# Iterate through each item key in the DataFrame
for item_key in df_not_zotero_id['zotero_item_key']:
    # Endpoint to get item bibliography
    endpoint = f'/groups/{user_id}/items/{item_key}'

    # Parameters for the request
    params = {
        'format': 'bib',
        'linkwrap': 1
    }

    # Make GET request to Zotero API
    response = requests.get(base_url + endpoint, params=params)

    # Check if request was successful
    if response.status_code == 200:
        bibliography = response.text.strip()  # Strip any leading/trailing whitespace
        bibliographies.append(bibliography)
        all_bibliographies += f'<p>{bibliography}</p><br><br>'  # Append bibliography with two newlines for separation
    else:
        error_message = f'Error fetching bibliography for item {item_key}: Status Code {response.status_code}'
        bibliographies.append(error_message)
        all_bibliographies += f'<p>{error_message}</p><br><br>'

# Add bibliographies to the original DataFrame
df_not_zotero_id['bibliography'] = bibliographies

df_zotero_id = pd.read_csv('zotero_citation_format.csv', index_col=False)
df_zotero_id = df_zotero_id.drop(columns={'Unnamed: 0'})
df_zotero_id = pd.concat([df_zotero_id, df_not_zotero_id]).reset_index(drop=True)

df_zotero_id.to_csv('zotero_citation_format.csv')
