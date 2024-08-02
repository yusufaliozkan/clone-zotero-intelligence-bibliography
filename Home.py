import streamlit as st
import pandas as pd

# home_page = st.Page('Home.py', title='Affiliation finder')

home = st.Page('Home_page.py', title='Home')
intelligence_history = st.Page('pages/1_Intelligence_history.py', title='Intelligence history')
intelligence_studies = st.Page('pages/2_Intelligence_studies.py', title='Intelligence studies')
intelligence_analysis = st.Page('pages/3_Intelligence_analysis.py', title='Intelligence analysis')

pg = st.navigation(
    {
        'Home':[home],
        'Collections':[
            intelligence_history, 
            intelligence_studies,
            intelligence_analysis
            ]
    }
)
    
pg.run()
