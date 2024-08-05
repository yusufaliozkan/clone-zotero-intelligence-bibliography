import streamlit as st
import pandas as pd

# home_page = st.Page('Home.py', title='Affiliation finder')

home = st.Page('Home_page.py', title='Home')
intelligence_history = st.Page('pages/1_Intelligence history.py', title='Intelligence history')
intelligence_studies = st.Page('pages/2_Intelligence studies.py', title='Intelligence studies')
intelligence_analysis = st.Page('pages/3_Intelligence analysis.py', title='Intelligence analysis')
intelligence_organisations = st.Page('pages/4_Intelligence organisations.py', title='Intelligence organisations')
intelligence_failures = st.Page('pages/5_Intelligence failures.py', title='Intelligence failures')
intelligence_oversight = st.Page('pages/6_Intelligence oversight and ethics.py', title='Intelligence oversight and ethics')
intelligence_collection = st.Page('pages/7_Intelligence collection.py', title='Intelligence collection')
counterintelligence = st.Page('pages/8_Counterintelligence.py')
covert_action = st.Page('pages/9_Covert action.py')

pg = st.navigation(
    {
        'Home':[home],
        'Collections':[
            intelligence_history, 
            intelligence_studies,
            intelligence_analysis,
            intelligence_organisations,
            intelligence_failures,
            intelligence_oversight,
            intelligence_collection,
            counterintelligence,
            covert_action
            ]
    }
)
    
pg.run()