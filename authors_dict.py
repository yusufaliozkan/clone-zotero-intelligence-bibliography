import pandas as pd

name_replacements = {
    'David Gioe': 'David V. Gioe',
    'David V Gioe':'David V. Gioe',
    'David Vincent Gioe': 'David V. Gioe',
    'Michael Goodman': 'Michael S. Goodman',
    'Michael S Goodman': 'Michael S. Goodman',
    'Michael Simon Goodman': 'Michael S. Gacoodman',
    'Thomas Maguire':'Thomas J. Maguire',
    'Thomas Joseph Maguire':'Thomas J. Maguire',
    'Huw John Davies':'Huw J. Davies',
    'Huw Davies':'Huw J. Davies',
    'Philip H.J. Davies':'Philip H. J. Davies',
    'Philip Davies':'Philip H. J. Davies',
    'Dan Lomas':'Daniel W. B. Lomas',
    'Daniel W B Lomas':'Daniel W. B. Lomas',
    'Daniel W.B. Lomas':'Daniel W. B. Lomas',
    'Richard Aldrich':'Richard J. Aldrich',
    'Richard J Aldrich':'Richard J. Aldrich',
    'Steven Wagner':'Steven B. Wagner',
    'Daniel Larsen':'Daniel R. Larsen',
    'Daniel Richard Larsen':'Daniel R. Larsen',
    'Loch Johnson':'Loch K. Johnson',
    'Sir David Omand Gcb':'David Omand',
    'Sir David Omand':'David Omand',
    'John Ferris':'John R. Ferris',
    'John Robert Ferris':'John R. Ferris',
    'Richard Betts':'Richard K. Betts',
    'Wesley Wark':'Wesley K. Wark',
    'Michael Handel':'Michael I. Handel',
    'Michael I Handel':'Michael I. Handel',
    'Matthew Seligmann':'Matthew S. Seligmann',
    'Christopher Andrew':'Christopher M. Andrew',
    'STEPHEN MARRIN':'Stephen Marrin',
    'Christopher Moran':'Christopher R. Moran',
    'Christopher R Moran':'Christopher R. Moran',
    'Richard Popplewell':'Richard J. Popplewell',
    'Richard James Popplewell':'Richard J. Popplewell',
    'Paul Michael McGarr':'Paul M. McGarr',
    'Paul McGarr':'Paul M. McGarr',
    'John Paul Maddrell':'John P. Maddrell',
    'John Maddrell':'John P. Maddrell',
    'Paul Maddrell':'John P. Maddrell',
    'C.G. McKay':'C. G. McKay',
    'C. G. Mckay':'C. G. McKay',
    'C.G. Mckay':'C. G. McKay',
    'David Mcknight':'David McKnight',
    'Julie Mendosa':'Julie A. Mendosa',
    'Robert Jervis 1':'Robert Jervis',
    'Ben B. Fischer':'Benjamin B. Fischer',
    'Benjamin Fischer':'Benjamin B. Fischer',
    "Eunan O'halpin":"Eunan O'Halpin",
    "Eunan O’Halpin":"Eunan O'Halpin",
    'Yusuf Ozkan':'Yusuf A. Ozkan',
    'Yusuf Ali Ozkan':'Yusuf A. Ozkan',
    'Stephen Coulthart':'Stephen J. Coulthart',
    'Kevin Riehle':'Kevin P. Riehle',
    'James Wirtz':'James J. Wirtz',
    'James J Wirtz':'James J. Wirtz',
    'Philip HJ Davies':'Philip H. J. Davies',
    'Jeff Rogg':'Jeffrey P. Rogg',
    'Celia G. Parker':'Celia G. Parker-Vincent',
    'Celia Parker-Vincent':'Celia G. Parker-Vincent',
    'G. H. Bennett':'Gill Bennett',
    'Emrah Safa Gürkan':'Emrah Safa Gurkan'
}

def get_df_authors():
    df_authors = pd.read_csv('all_items.csv')
    df_authors['Author_name'] = df_authors['FirstName2'].apply(lambda x: x.split(', ') if isinstance(x, str) and x else x)
    df_authors = df_authors.explode('Author_name')
    df_authors.reset_index(drop=True, inplace=True)
    df_authors = df_authors.dropna(subset=['FirstName2'])
    df_authors['Author_name'] = df_authors['Author_name'].map(name_replacements).fillna(df_authors['Author_name'])
    return df_authors
