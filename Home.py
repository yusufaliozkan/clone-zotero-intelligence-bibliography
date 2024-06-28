from pyzotero import zotero
import pandas as pd
import streamlit as st
from IPython.display import HTML
import streamlit.components.v1 as components
import numpy as np
import altair as alt
# from pandas.io.json import json_normalize
from datetime import date, timedelta  
from datetime import datetime
import datetime
from streamlit_extras.switch_page_button import switch_page
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
# import gsheetsdb as gdb
from streamlit_gsheets import GSheetsConnection
import datetime as dt
import time
import PIL
from PIL import Image, ImageDraw, ImageFilter
import json
from authors_dict import df_authors, name_replacements
from copyright import display_custom_license
from sidebar_content import sidebar_content
import plotly.graph_objs as go
import feedparser
import requests
from format_entry import format_entry
from streamlit_dynamic_filters import DynamicFilters
# from rss_feed import df_podcast, df_magazines

# Connecting Zotero with API 
library_id = '2514686'
library_type = 'group'
api_key = '' # api_key is only needed for private groups and libraries

# Bringing recently changed items

st.set_page_config(layout = "wide", 
                    page_title='Intelligence studies network',
                    page_icon="https://images.pexels.com/photos/315918/pexels-photo-315918.png",
                    initial_sidebar_state="auto") 
pd.set_option('display.max_colwidth', None)


pages = [
        st.Page('Home.py', title='Home page'),
        st.Page('pages/1_Intelligence history.py', title='History'),
        st.Page('pages/2_Intelligence studies.py', title='Intel studies')
    ]

pg = st.navigation(pages)


zot = zotero.Zotero(library_id, library_type)
@st.cache_data(ttl=600)
def zotero_data(library_id, library_type):
    items = zot.top(limit=10)
    items = sorted(items, key=lambda x: x['data']['dateAdded'], reverse=True)
    data=[]
    columns = ['Title','Publication type', 'Link to publication', 'Abstract', 'Zotero link', 'Date added', 'Date published', 'Date modified', 'Col key', 'Authors', 'Pub_venue', 'Book_title']

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
        item['data'].get('bookTitle')
        ))
    df = pd.DataFrame(data, columns=columns)
    return df

df = zotero_data(library_id, library_type)


pg.run()