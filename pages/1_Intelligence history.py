from pyzotero import zotero
import pandas as pd
import streamlit as st
from IPython.display import HTML
import streamlit.components.v1 as components
import numpy as np
import altair as alt
# from pandas.io.json import json_normalize
import datetime
import plotly.express as px
import numpy as np
import re
import matplotlib.pyplot as plt
import nltk
nltk.download('all')
from nltk.corpus import stopwords
nltk.download('stopwords')
from wordcloud import WordCloud
# from gsheetsdb import connect
from streamlit_gsheets import GSheetsConnection
import datetime as dt     
import random
from authors_dict import df_authors, name_replacements
from sidebar_content import sidebar_content 
from format_entry import format_entry
from copyright import display_custom_license
from events import evens_conferences
from streamlit_dynamic_filters import DynamicFilters
import requests
from st_keyup import st_keyup
from collection_template import collection_template 

st.set_page_config(layout = "wide", 
                    page_title='Intelligence history',
                    page_icon="https://images.pexels.com/photos/315918/pexels-photo-315918.png",
                    initial_sidebar_state="auto") 

st.title("Intelligence history")

with st.spinner('Retrieving data & updating dashboard...'):

    # # Connecting Zotero with API
    # library_id = '2514686' # intel 2514686
    # library_type = 'group'
    # api_key = '' # api_key is only needed for private groups and libraries

    sidebar_content()

    # zot = zotero.Zotero(library_id, library_type)

    # @st.cache_data(ttl=300)
    # def zotero_collections(library_id, library_type):
    #     collections = zot.collections()
    #     data2=[]
    #     columns2 = ['Key','Name', 'Link']
    #     for item in collections:
    #         data2.append((item['data']['key'], item['data']['name'], item['links']['alternate']['href']))
    #     pd.set_option('display.max_colwidth', None)
    #     df_collections = pd.DataFrame(data2, columns=columns2)
    #     return df_collections
    # df_collections = zotero_collections(library_id, library_type)

    df_collections = pd.read_csv('all_items_duplicated.csv')
    # df_collections = df_collections[~df_collections['Collection_Name'].str.contains('01.98')]
    df_collections = df_collections[df_collections['Collection_Name'] != '01 Intelligence history']


    df_collections = df_collections.sort_values(by='Collection_Name')
    df_collections=df_collections[df_collections['Collection_Name'].str.contains("01.")]
    df_collections = collection_template()
    collection_template()