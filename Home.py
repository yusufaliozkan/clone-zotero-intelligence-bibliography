import streamlit as st
import pandas as pd

# home_page = st.Page('Home.py', title='Affiliation finder')

home = st.Page('Home_page.py', title='Home')
intelligence_history = st.Page('pages/1_Intelligence history.py', title='Intelligence history')
intelligence_studies = st.Page('pages/2_Intelligence studies.py', title='Intelligence studies')
intelligence_analysis = st.Page('pages/3_Intelligence analysis.py', title='Intelligence analysis')
intelligence_organisations = st.Page('pages/4_Intelligence organisations.py', title='Intelligence organisations')

pg = st.navigation(
    {
        'Home':[home],
        'Collections':[
            intelligence_history, 
            intelligence_studies,
            intelligence_analysis,
            intelligence_organisations
            ]
    }
)
    
pg.run()