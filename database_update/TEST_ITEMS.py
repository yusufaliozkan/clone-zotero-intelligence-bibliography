import pandas as pd
import json, sys
import requests


### RETRIEVING CITATION COUNT AND OA STATUS FROM OPENALEX
data = {
    'Zotero link':['LINK1'],
    'DOI':['10.1126/science.185.4157.1124']
}
df_doi = pd.DataFrame(data)
# df_doi = df.copy()

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

df_doi = df_doi.drop(columns=['DOI'])
df = pd.merge(df, df_doi, on='Zotero link', how='left')
duplicated_df = pd.merge(duplicated_df, df_doi, on='Zotero link', how='left')

df.to_csv('all_items.csv')
duplicated_df.to_csv('all_items_duplicated.csv')
df_countries.to_csv('countries.csv',index=False)