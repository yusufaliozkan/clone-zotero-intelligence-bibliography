from pyzotero import zotero
import pandas as pd
import streamlit as st
import numpy as np
import altair as alt
from datetime import date
import datetime
from streamlit_extras.switch_page_button import switch_page
import plotly.express as px
import plotly.graph_objs as go
import re
import matplotlib.pyplot as plt
import nltk
nltk.download("all", quiet=True)
import pydeck as pdk
from countryinfo import CountryInfo
from streamlit_theme import st_theme
from st_keyup import st_keyup
import json

from authors_dict import get_df_authors, name_replacements
from copyright import display_custom_license
from sidebar_content import sidebar_content, set_page_config
from format_entry import format_entry
from events import evens_conferences

from shared_utils import (
    parse_date_column,
    sort_by_date,
    load_reviews_map,
    render_wordcloud,
    split_and_expand,
    remove_numbers,
    convert_df_to_csv,
    render_metrics,
    render_report_charts,
    display_bibliographies,
    sort_radio,
    render_paginated_list,
)

# ── Zotero connection ───────────────────────────────────────────────────────
library_id = "2514686"
library_type = "group"
api_key = ""

set_page_config()
pd.set_option("display.max_colwidth", None)
zot = zotero.Zotero(library_id, library_type)

# ── Theme-aware logo ────────────────────────────────────────────────────────
theme = st_theme()
image_path = (
    "images/01_logo/IntelArchive_Digital_Logo_Colour-Negative.svg"
    if theme and theme.get("base") == "dark"
    else "images/01_logo/IntelArchive_Digital_Logo_Colour-Positive.svg"
)
with open(image_path) as f:
    st.image(f.read(), width=200)

st.subheader("Intelligence Studies Database", anchor=False)

cite_today = datetime.date.today().strftime("%d %B %Y")
intro = f"""
Welcome to **IntelArchive**.
The IntelArchive is one of the most comprehensive databases listing sources on intelligence studies and history.

Join our Google Groups to get updates and learn new features about the website and the database.
You can also ask questions or make suggestions. (https://groups.google.com/g/intelarchive)

Resources about the website:

Ozkan, Yusuf A. "'Intelligence Studies Network': A Human-Curated Database for Indexing Resources with Open-Source Tools." arXiv, August 7, 2024. https://doi.org/10.48550/arXiv.2408.03868.

Ozkan, Yusuf A. 'Intelligence Studies Network Dataset'. Zenodo, 15 August 2024. https://doi.org/10.5281/zenodo.13325699.

**Cite this page:** IntelArchive. '*Intelligence Studies Network*', Created 1 June 2020, Accessed {cite_today}. https://intelligence.streamlit.app/.
"""

# ── Load data ───────────────────────────────────────────────────────────────
with st.spinner("Retrieving data..."):
    df_dedup        = pd.read_csv("all_items.csv")
    df_dedup["parentKey"] = df_dedup["Zotero link"].str.split("/").str[-1]
    df_duplicated   = pd.read_csv("all_items_duplicated.csv")
    df_authors      = get_df_authors()
    df_book_reviews = pd.read_csv("book_reviews.csv")

    col1, col2, col3 = st.columns([3, 5, 8])
    with col3:
        with st.expander("Introduction"):
            st.info(intro)

    df_intro = df_dedup.copy()
    df_intro["Date added"] = pd.to_datetime(df_intro["Date added"])
    current_date = pd.to_datetime("now", utc=True)
    items_this_month = df_intro[
        (df_intro["Date added"].dt.year  == current_date.year) &
        (df_intro["Date added"].dt.month == current_date.month)
    ]
    with col1:
        st.metric(
            label="Number of items in the library",
            value=len(df_intro),
            delta=len(items_this_month),
            help=f"**{len(items_this_month)}** items added in {current_date.strftime('%B %Y')}",
        )

    st.write("The library last updated on **" + df_intro.loc[0]["Date added"].strftime("%d/%m/%Y, %H:%M") + "**")

    with col2:
        with st.popover("More metrics"):
            citation_count  = df_dedup["Citation"].sum()
            non_nan_cited   = df_dedup.dropna(subset=["Citation_list"])
            citation_mean   = non_nan_cited["Citation"].mean()
            citation_median = non_nan_cited["Citation"].median()
            outlier_count   = int((df_dedup["Citation"] > 1000).sum())
            avg_wo_outliers = round(df_dedup.loc[df_dedup["Citation"] < 1000, "Citation"].mean(), 2)

            st.metric(label="Number of citations", value=int(citation_count),
                      help="Citations from [OpenAlex](https://openalex.org/).")
            st.metric(label="Average citation",
                      value=round(df_dedup["Citation"].mean(), 2),
                      help=f"**{outlier_count}** outliers >1000. Without outliers: **{avg_wo_outliers}**. Median: **{round(citation_median,1)}**.")

            ja = df_dedup[df_dedup["Publication type"] == "Journal article"]
            oa_ratio = (ja["OA status"].sum() / len(ja) * 100) if len(ja) else 0
            st.metric(label="Open access coverage", value=f"{int(oa_ratio)}%", help="Journal articles only")
            st.metric(label="Number of publication types", value=int(df_dedup["Publication type"].nunique()))

            df_no_thesis = df_dedup[df_dedup["Publication type"] != "Thesis"]
            expanded      = split_and_expand(df_no_thesis["FirstName2"])
            author_no     = len(expanded)
            item_count    = len(df_no_thesis)
            st.metric(label="Number of authors", value=int(author_no))
            st.metric(label="Author/publication ratio", value=round(author_no / item_count, 2))
            multi = df_no_thesis["FirstName2"].astype(str).apply(lambda x: "," in x).sum()
            st.metric(label="Collaboration ratio", value=f"{round(multi/item_count*100,1)}%")

    sidebar_content()

    tab1, tab2 = st.tabs(["📑 Publications", "📊 Dashboard"])

    # ════════════════════════════════════════════════════════════════════════
    # TAB 1
    # ════════════════════════════════════════════════════════════════════════
    with tab1:
        col1, col2 = st.columns([6, 2])
        with col1:

            def parse_search_terms(search_term):
                tokens = re.findall(r'(?:"[^"]*"|\S+)', search_term)
                boolean_tokens = []
                for token in tokens:
                    if token in ("AND", "OR", "NOT"):
                        boolean_tokens.append(token)
                    else:
                        if token.startswith('"') and token.endswith('"'):
                            stripped = token.strip('"')
                        else:
                            stripped = re.sub(r"[^a-zA-Z0-9\s'\-\u2013]", "", token)
                            stripped = stripped.replace("(", "").replace(")", "")
                        boolean_tokens.append(stripped.strip('"'))
                while boolean_tokens and boolean_tokens[-1] in ("AND", "OR", "NOT"):
                    boolean_tokens.pop()
                return boolean_tokens

            def apply_boolean_search(df, tokens, search_in):
                if not tokens:
                    return df
                query = ""
                negate_next = False
                for token in tokens:
                    if token == "AND":
                        query += " & "; negate_next = False
                    elif token == "OR":
                        query += " | "; negate_next = False
                    elif token == "NOT":
                        negate_next = True
                    else:
                        esc = re.escape(token)
                        if search_in == "Title and abstract":
                            cond = f'(Title.str.contains(r"\\b{esc}\\b", case=False, na=False) | Abstract.str.contains(r"\\b{esc}\\b", case=False, na=False))'
                        else:
                            cond = f'Title.str.contains(r"\\b{esc}\\b", case=False, na=False)'
                        if negate_next:
                            cond = f"~({cond})"; negate_next = False
                        if query and query.strip()[-1] not in "&|(":
                            query += " & "
                        query += cond
                try:
                    return df.query(query, engine="python")
                except Exception:
                    return pd.DataFrame()

            st.header("Search in database", anchor=False)
            st.write('<style>div.row-widget.stRadio > div{flex-direction:row;}</style>', unsafe_allow_html=True)

            OPTION_MAP = {
                0: "Search keywords",
                1: "Search author",
                2: "Search collection",
                3: "Publication types",
                4: "Search journal",
                5: "Publication year",
                6: "Cited papers",
            }
            search_option = st.pills(
                "Select search option",
                options=list(OPTION_MAP.keys()),
                format_func=lambda o: OPTION_MAP[o],
                selection_mode="single",
                default=0,
            )

            # ================================================================
            # 0 – KEYWORD SEARCH
            # ================================================================
            if search_option == 0:
                st.subheader("Search keywords", anchor=False, divider="blue")

                @st.fragment
                def search_keyword():
                    reviews_map = load_reviews_map()

                    @st.dialog("Search guide")
                    def guide(_):
                        st.write("""
                            Supports Boolean operators: **AND**, **OR**, **NOT**.
                            Double-quotes for phrases (e.g. "covert action").
                            Parentheses are **not** supported.
                            Share your search: https://intelligence.streamlit.app/?search_in=Title&query=cia+OR+mi6
                        """)

                    if "guide" not in st.session_state:
                        if st.button("Search guide"):
                            guide("Search guide")

                    def update_search_params():
                        st.session_state.search_term = st.session_state.search_term_input
                        st.query_params.from_dict({
                            "search_in": st.session_state.search_in,
                            "query": st.session_state.search_term,
                        })

                    qp = st.query_params
                    for k, default in [("search_term",       qp.get("query",     "")),
                                       ("search_in",         qp.get("search_in", "Title")),
                                       ("search_term_input", qp.get("query",     ""))]:
                        if k not in st.session_state:
                            st.session_state[k] = default

                    search_options = ["Title", "Title and abstract"]
                    try:
                        si_index = search_options.index(qp.get("search_in", "Title"))
                    except ValueError:
                        si_index = 0

                    cols, cola = st.columns([2, 6])
                    with cols:
                        st.session_state.search_in = st.selectbox(
                            "Search in", search_options, index=si_index,
                            on_change=update_search_params,
                        )
                    with cola:
                        st.text_input(
                            "Search keywords in titles or abstracts",
                            st.session_state.search_term_input,
                            key="search_term_input",
                            placeholder="Type your keyword(s)",
                            on_change=update_search_params,
                        )

                    search_term = st.session_state.search_term.strip()
                    if not search_term:
                        st.info("Please enter a keyword to search in title or abstract.")
                        return

                    with st.status(f"Searching publications for '**{search_term}**'...", expanded=True) as status:
                        tokens      = parse_search_terms(search_term)
                        df_csv      = df_duplicated.copy()
                        filtered_df = apply_boolean_search(df_csv, tokens, st.session_state.search_in)
                        filtered_df_for_collections = filtered_df.copy()
                        filtered_df = filtered_df.drop_duplicates()

                        if not filtered_df.empty and "Date published" in filtered_df.columns:
                            filtered_df["Date published"] = parse_date_column(filtered_df["Date published"])
                            filtered_df["Date published"] = filtered_df["Date published"].fillna("")
                            filtered_df = sort_by_date(filtered_df).sort_values(
                                ["No date flag", "Date published"], ascending=[True, True])

                        types       = filtered_df["Publication type"].dropna().unique()
                        collections = filtered_df["Collection_Name"].dropna().unique()

                        cs1, cs2, cs3, cs4 = st.columns(4)
                        with cs1:
                            c_metric = st.container()
                        with cs2:
                            with st.popover("More metrics"):
                                c_cit      = st.container()
                                c_cit_avg  = st.container()
                                c_oa       = st.container()
                                c_type     = st.container()
                                c_auth_no  = st.container()
                                c_auth_rat = st.container()
                                c_collab   = st.container()
                        with cs3:
                            with st.popover("Relevant themes"):
                                st.markdown("##### Top relevant publication themes")
                                fdc = filtered_df_for_collections[
                                    ["Zotero link","Collection_Key","Collection_Name","Collection_Link"]
                                ].copy()
                                fdc2 = fdc["Collection_Name"].value_counts().reset_index().head(5)
                                fdc2.columns = ["Collection_Name","Number_of_Items"]
                                fdc  = pd.merge(fdc2, fdc, on="Collection_Name", how="left").drop_duplicates("Collection_Name").reset_index(drop=True)
                                fdc["Collection_Name"] = fdc["Collection_Name"].apply(remove_numbers)
                                for i, row in fdc.iterrows():
                                    st.caption(f"{i+1}) [{row['Collection_Name']}]({row['Collection_Link']}) {row['Number_of_Items']} items")
                        with cs4:
                            with st.popover("Filters and more"):
                                types2       = st.multiselect("Publication types", types, key="kw_types")
                                collections2 = st.multiselect("Collection", collections, key="kw_collections")
                                c_dl         = st.container()
                                display_abstracts = st.checkbox("Display abstracts")
                                only_cited   = st.checkbox("Show cited items only")
                                view         = st.radio("View as:", ("Basic list","Table","Bibliography"), horizontal=True)

                        if types2:
                            filtered_df = filtered_df[filtered_df["Publication type"].isin(types2)]
                        if collections2:
                            filtered_df = filtered_df[filtered_df["Collection_Name"].isin(collections2)]
                        if only_cited:
                            filtered_df = filtered_df[(filtered_df["Citation"].notna()) & (filtered_df["Citation"] != 0)]
                        filtered_df = filtered_df.drop_duplicates(subset=["Zotero link"], keep="first")
                        num_items   = len(filtered_df)

                        if num_items:
                            render_metrics(
                                filtered_df,
                                container_metric=c_metric,
                                container_citation=c_cit,
                                container_citation_average=c_cit_avg,
                                container_oa=c_oa,
                                container_type=c_type,
                                container_author_no=c_auth_no,
                                container_author_pub_ratio=c_auth_rat,
                                container_publication_ratio=c_collab,
                            )
                            csv = convert_df_to_csv(
                                filtered_df[["Publication type","Title","Abstract","Date published",
                                             "Publisher","Journal","Link to publication","Zotero link","Citation"]]
                                .assign(Abstract=lambda d: d["Abstract"].str.replace("\n"," "))
                                .reset_index(drop=True)
                            )
                            c_dl.download_button(
                                "Download search", csv,
                                f"search-result-{datetime.date.today().isoformat()}.csv",
                                mime="text/csv", key="dl-kw", icon=":material/download:",
                            )
                            on = st.toggle(":material/monitoring: Generate report")
                            if on:
                                st.info(f"Dashboard for: {search_term}")
                                render_report_charts(filtered_df, search_term, name_replacements,
                                                     show_themes=True, themes_df=fdc)
                            else:
                                filtered_df = sort_radio(filtered_df, key="kw_sort")
                                if view == "Basic list":
                                    articles  = [format_entry(row, include_citation=True, reviews_map=reviews_map) for _, row in filtered_df.iterrows()]
                                    abstracts = [row["Abstract"] if pd.notnull(row["Abstract"]) else "N/A" for _, row in filtered_df.iterrows()]
                                    render_paginated_list(filtered_df, articles, abstracts,
                                                          display_abstracts=display_abstracts,
                                                          search_tokens=tokens,
                                                          search_in=st.session_state.search_in)
                                elif view == "Table":
                                    st.dataframe(
                                        filtered_df[["Publication type","Title","Date published","FirstName2",
                                                     "Abstract","Publisher","Journal","Collection_Name",
                                                     "Link to publication","Zotero link"]]
                                        .rename(columns={"FirstName2":"Author(s)","Collection_Name":"Collection",
                                                         "Link to publication":"Publication link"})
                                    )
                                elif view == "Bibliography":
                                    filtered_df["zotero_item_key"] = filtered_df["Zotero link"].str.replace(
                                        "https://www.zotero.org/groups/intelarchive_intelligence_studies_database/items/","")
                                    df_zot = pd.read_csv("zotero_citation_format.csv")
                                    display_bibliographies(pd.merge(filtered_df, df_zot, on="zotero_item_key", how="left"))
                        else:
                            c_metric.metric(label="Number of items found", value=0)
                            st.write("No articles found with the given keyword/phrase.")

                        status.update(
                            label=f"Search found **{num_items}** {'matching source' if num_items == 1 else 'matching sources'} for '**{search_term}**'.",
                            state="complete", expanded=True,
                        )

                search_keyword()

            # ================================================================
            # 1 – AUTHOR SEARCH
            # ================================================================
            elif search_option == 1:
                st.query_params.clear()
                st.subheader("Search author", anchor=False, divider="blue")

                @st.fragment
                def search_author():
                    reviews_map    = load_reviews_map()
                    pub_counts     = df_authors["Author_name"].value_counts().to_dict()
                    sorted_authors = sorted(df_authors["Author_name"].unique(),
                                            key=lambda a: pub_counts.get(a, 0), reverse=True)
                    options          = [""] + [f"{a} ({pub_counts.get(a,0)})" for a in sorted_authors]
                    selected_display = st.selectbox("Select author", options)
                    selected_author  = selected_display.split(" (")[0] if selected_display else None

                    if not selected_author:
                        st.write("Select an author to see items")
                        return

                    adf = df_authors[df_authors["Author_name"] == selected_author].copy()
                    adf["Date published"] = parse_date_column(adf["Date published"])
                    adf["Date published"] = adf["Date published"].fillna("")
                    adf = sort_by_date(adf).sort_values(["No date flag","Date published"], ascending=[True,True])

                    with st.expander("Click to expand", expanded=True):
                        st.subheader(f"Publications by {selected_author}", anchor=False, divider="blue")
                        ca1, ca2, ca3, ca4 = st.columns(4)
                        with ca1: c_m = st.container()
                        with ca2:
                            with st.popover("More metrics"):
                                c_cit     = st.container()
                                c_cit_avg = st.container()
                                c_oa      = st.container()
                                c_type    = st.container()
                                c_collab  = st.container()
                        with ca3:
                            with st.popover("Relevant themes"):
                                st.markdown("##### Top 5 relevant themes")
                                fdc  = pd.merge(df_duplicated, adf[["Zotero link"]], on="Zotero link")
                                fdc  = fdc[["Zotero link","Collection_Key","Collection_Name","Collection_Link"]]
                                fdc2 = fdc["Collection_Name"].value_counts().reset_index().head(10)
                                fdc2.columns = ["Collection_Name","Number_of_Items"]
                                fdc2 = fdc2[fdc2["Collection_Name"] != "01 Intelligence history"]
                                fdc  = pd.merge(fdc2, fdc, on="Collection_Name", how="left").drop_duplicates("Collection_Name").reset_index(drop=True)
                                fdc["Collection_Name"] = fdc["Collection_Name"].apply(remove_numbers)
                                for i, row in fdc.iterrows():
                                    st.caption(f"{i+1}) [{row['Collection_Name']}]({row['Collection_Link']}) {row['Number_of_Items']} items")
                        with ca4:
                            with st.popover("Filters and more"):
                                c_types_filter = st.container()
                                c_dl           = st.container()
                                view = st.radio("View as:", ("Basic list","Table","Bibliography"), horizontal=True)

                        st.write("*This database **may not show** all research outputs of the author.*")
                        types = c_types_filter.multiselect(
                            "Publication type", adf["Publication type"].unique(),
                            adf["Publication type"].unique(), key="auth_types",
                        )
                        adf = adf[adf["Publication type"].isin(types)].reset_index(drop=True)

                        render_metrics(adf, container_metric=c_m, container_citation=c_cit,
                                       container_citation_average=c_cit_avg, container_oa=c_oa,
                                       container_type=c_type, container_publication_ratio=c_collab)

                        csv = convert_df_to_csv(
                            adf[["Publication type","Title","Abstract","Date published",
                                 "Publisher","Journal","Link to publication","Zotero link","Citation"]]
                            .assign(Abstract=lambda d: d["Abstract"].str.replace("\n"," "))
                        )
                        c_dl.download_button(
                            "Download publications", csv,
                            f"{selected_author}_{datetime.date.today().isoformat()}.csv",
                            mime="text/csv", key="dl-auth", icon=":material/download:",
                        )

                        on = st.toggle(":material/monitoring: Generate report")
                        if on and len(adf):
                            st.info(f"Publications report for {selected_author}")
                            render_report_charts(adf, selected_author, name_replacements,
                                                 show_themes=True, themes_df=fdc)
                        elif not on:
                            adf = sort_radio(adf, key="auth_sort")
                            if view == "Basic list":
                                for i, row in adf.iterrows():
                                    st.write(f"{i+1}) {format_entry(row, include_citation=True, reviews_map=reviews_map)}")
                            elif view == "Table":
                                st.dataframe(
                                    adf[["Publication type","Title","Date published","FirstName2",
                                         "Abstract","Publisher","Journal","Citation",
                                         "Link to publication","Zotero link"]]
                                    .rename(columns={"FirstName2":"Author(s)","Link to publication":"Publication link"})
                                )
                            elif view == "Bibliography":
                                adf["zotero_item_key"] = adf["Zotero link"].str.replace(
                                    "https://www.zotero.org/groups/intelarchive_intelligence_studies_database/items/","")
                                df_zot = pd.read_csv("zotero_citation_format.csv")
                                display_bibliographies(pd.merge(adf, df_zot, on="zotero_item_key", how="left"))
                        else:
                            st.write("No publication type selected.")

                search_author()

            # ================================================================
            # 2 – COLLECTION SEARCH
            # ================================================================
            elif search_option == 2:
                st.query_params.clear()
                st.subheader("Search collection", anchor=False, divider="blue")

                @st.fragment
                def search_collection():
                    reviews_map  = load_reviews_map()
                    df_csv_col   = df_duplicated.copy()
                    df_csv_col["Collection_Name"] = df_csv_col["Collection_Name"].apply(remove_numbers)
                    excluded     = {"KCL intelligence","Events","Journals",""}
                    col_counts   = df_csv_col["Collection_Name"].value_counts()
                    sorted_cols  = [c for c in col_counts.index if c not in excluded]
                    options      = [""] + [f"{c} [{col_counts[c]} items]" for c in sorted_cols]
                    sel_display  = st.selectbox("Select a collection", options)
                    selected_col = sel_display.rsplit(" [", 1)[0] if sel_display else None

                    if not selected_col:
                        st.write("Pick a collection to see items")
                        return

                    cdf = df_csv_col[df_csv_col["Collection_Name"] == selected_col].copy()
                    cdf["Date published"] = parse_date_column(cdf["Date published"])
                    cdf["Date published"] = cdf["Date published"].fillna("")
                    cdf = sort_by_date(cdf).sort_values(["No date flag","Date published"], ascending=[True,True])
                    collection_link = cdf["Collection_Link"].iloc[0]

                    with st.expander("Click to expand", expanded=True):
                        st.markdown(f"#### Collection theme: {selected_col}")
                        cc1, cc2, cc3 = st.columns(3)
                        with cc1: c_m = st.container()
                        with cc2:
                            with st.popover("More metrics"):
                                c_cit      = st.container()
                                c_cit_avg  = st.container()
                                c_oa       = st.container()
                                c_type     = st.container()
                                c_auth_no  = st.container()
                                c_auth_rat = st.container()
                                c_collab   = st.container()
                        with cc3:
                            with st.popover("Filters and more"):
                                c_info   = st.container()
                                c_filter = st.container()
                                c_dl     = st.container()
                                view = st.radio("View as:", ("Basic list","Table","Bibliography"), horizontal=True)

                        c_info.info(f"See the collection in [Zotero]({collection_link})")
                        types = c_filter.multiselect(
                            "Publication type", cdf["Publication type"].unique(),
                            cdf["Publication type"].unique(), key="col_types",
                        )
                        cdf = cdf[cdf["Publication type"].isin(types)].reset_index(drop=True)

                        render_metrics(cdf, container_metric=c_m, container_citation=c_cit,
                                       container_citation_average=c_cit_avg, container_oa=c_oa,
                                       container_type=c_type, container_author_no=c_auth_no,
                                       container_author_pub_ratio=c_auth_rat,
                                       container_publication_ratio=c_collab)

                        csv = convert_df_to_csv(
                            cdf[["Publication type","Title","Abstract","Date published",
                                 "Publisher","Journal","Link to publication","Zotero link","Citation"]]
                            .assign(Abstract=lambda d: d["Abstract"].str.replace("\n"," "))
                            .reset_index(drop=True)
                        )
                        c_dl.download_button(
                            "Download the collection", csv,
                            f"{selected_col}_{datetime.date.today().isoformat()}.csv",
                            mime="text/csv", key="dl-col", icon=":material/download:",
                        )

                        on = st.toggle(":material/monitoring: Generate report")
                        if on and len(cdf):
                            st.info(f"Report for {selected_col}")
                            render_report_charts(cdf, selected_col, name_replacements)
                        elif not on:
                            cdf = sort_radio(cdf, key="col_sort")
                            if len(cdf) > 20 and st.checkbox("Show only first 20 items (untick to see all)", value=True):
                                cdf = cdf.head(20)
                            if view == "Basic list":
                                for i, row in cdf.iterrows():
                                    st.write(f"{i+1}) {format_entry(row, include_citation=True, reviews_map=reviews_map)}")
                            elif view == "Table":
                                st.dataframe(
                                    cdf[["Publication type","Title","Date published","FirstName2",
                                         "Abstract","Link to publication","Zotero link"]]
                                    .rename(columns={"FirstName2":"Author(s)","Link to publication":"Publication link"})
                                )
                            elif view == "Bibliography":
                                cdf["zotero_item_key"] = cdf["Zotero link"].str.replace(
                                    "https://www.zotero.org/groups/intelarchive_intelligence_studies_database/items/","")
                                df_zot = pd.read_csv("zotero_citation_format.csv")
                                display_bibliographies(pd.merge(cdf, df_zot, on="zotero_item_key", how="left"))
                        else:
                            st.write("No publication type selected.")

                search_collection()

            # ================================================================
            # 3 – PUBLICATION TYPES
            # ================================================================
            elif search_option == 3:
                st.query_params.clear()
                st.subheader("Publication types", anchor=False, divider="blue")

                @st.fragment
                def type_selection():
                    reviews_map   = load_reviews_map()
                    unique_types  = [""] + list(df_authors["Publication type"].unique())
                    selected_type = st.selectbox("Select a publication type", unique_types)
                    if not selected_type:
                        st.write("Pick a publication type to see items")
                        return

                    tdf = df_dedup[df_dedup["Publication type"] == selected_type].copy()
                    tdf["Date published"] = parse_date_column(tdf["Date published"])
                    tdf["Date published"] = tdf["Date published"].fillna("")
                    tdf = sort_by_date(tdf).sort_values(["No date flag","Date published"], ascending=[True,True])

                    with st.expander("Click to expand", expanded=True):
                        st.subheader(f"Publication type: {selected_type}", anchor=False, divider="blue")
                        if selected_type == "Thesis":
                            st.warning("Links to PhD theses may not work due to the [British Library cyber incident](https://www.bl.uk/cyber-incident/).")

                        ct1, ct2, ct3, ct4 = st.columns(4)
                        with ct1: c_m = st.container()
                        with ct2:
                            with st.popover("More metrics"):
                                c_cit      = st.container()
                                c_oa       = st.container()
                                c_collab   = st.container()
                                c_auth_no  = st.container()
                                c_auth_rat = st.container()
                        with ct3:
                            with st.popover("Relevant themes"):
                                st.markdown("##### Top relevant publication themes")
                                fdc  = pd.merge(df_duplicated, tdf[["Zotero link"]], on="Zotero link")
                                fdc  = fdc[["Zotero link","Collection_Key","Collection_Name","Collection_Link"]]
                                fdc2 = fdc["Collection_Name"].value_counts().reset_index().head(10)
                                fdc2.columns = ["Collection_Name","Number_of_Items"]
                                fdc  = pd.merge(fdc2, fdc, on="Collection_Name", how="left").drop_duplicates("Collection_Name").reset_index(drop=True)
                                fdc["Collection_Name"] = fdc["Collection_Name"].apply(remove_numbers)
                                for i, row in fdc.iterrows():
                                    st.caption(f"{i+1}) [{row['Collection_Name']}]({row['Collection_Link']}) {row['Number_of_Items']} items")
                        with ct4:
                            with st.popover("Filters and more"):
                                c_dl = st.container()
                                if selected_type == "Thesis":
                                    thesis_types = [""] + list(tdf["Thesis_type"].unique())
                                    sel_thesis   = st.selectbox("Select a thesis type", thesis_types)
                                    if sel_thesis:
                                        tdf = tdf[tdf["Thesis_type"] == sel_thesis]
                                    unis    = [""] + sorted(tdf["University"].astype(str).unique().tolist())
                                    sel_uni = st.selectbox("Select a university", unis)
                                    if sel_uni:
                                        tdf = tdf[tdf["University"] == sel_uni]
                                view = st.radio("View as:", ("Basic list","Table","Bibliography"), horizontal=True)

                        render_metrics(tdf, container_metric=c_m, container_citation=c_cit,
                                       container_citation_average=st.container(),
                                       container_oa=c_oa, container_author_no=c_auth_no,
                                       container_author_pub_ratio=c_auth_rat,
                                       container_publication_ratio=c_collab)

                        csv = convert_df_to_csv(
                            tdf[["Publication type","Title","Abstract","Date published",
                                 "Publisher","Journal","Link to publication","Zotero link","Citation"]]
                            .assign(Abstract=lambda d: d["Abstract"].str.replace("\n"," "))
                            .reset_index(drop=True)
                        )
                        c_dl.download_button(
                            "Download", csv,
                            f"{selected_type}_{datetime.date.today().isoformat()}.csv",
                            mime="text/csv", key="dl-type", icon=":material/download:",
                        )

                        on = st.toggle(":material/monitoring: Generate report")
                        if on and len(tdf):
                            st.info(f"Report for {selected_type}")
                            render_report_charts(tdf, selected_type, name_replacements,
                                                 show_themes=True, themes_df=fdc)
                        else:
                            tdf = sort_radio(tdf, key="type_sort")
                            if len(tdf) > 20 and st.checkbox("Show only first 20 items (untick to see all)", value=True):
                                tdf = tdf.head(20)
                            if view == "Basic list":
                                for i, row in tdf.iterrows():
                                    st.write(f"{i+1}) {format_entry(row, include_citation=True, reviews_map=reviews_map)}")
                            elif view == "Table":
                                st.dataframe(
                                    tdf[["Publication type","Title","Date published","FirstName2",
                                         "Abstract","Link to publication","Zotero link"]]
                                    .rename(columns={"FirstName2":"Author(s)","Link to publication":"Publication link"})
                                )
                            elif view == "Bibliography":
                                tdf["zotero_item_key"] = tdf["Zotero link"].str.replace(
                                    "https://www.zotero.org/groups/intelarchive_intelligence_studies_database/items/","")
                                df_zot = pd.read_csv("zotero_citation_format.csv")
                                display_bibliographies(pd.merge(tdf, df_zot, on="zotero_item_key", how="left"))

                type_selection()

            # ================================================================
            # 4 – JOURNAL SEARCH
            # ================================================================
            elif search_option == 4:
                st.query_params.clear()
                st.subheader("Search journal", anchor=False, divider="blue")

                @st.fragment
                def search_journal():
                    df_ja    = df_dedup[df_dedup["Publication type"] == "Journal article"].copy()
                    jcounts  = df_ja["Journal"].value_counts()
                    journals = st.multiselect("Select a journal", jcounts.index.tolist())
                    if not journals:
                        st.write("Pick a journal name to see items")
                        return

                    jdf = df_ja[df_ja["Journal"].isin(journals)].copy()
                    jdf["Date published"] = parse_date_column(jdf["Date published"])
                    jdf["Date published"] = jdf["Date published"].fillna("")
                    jdf = sort_by_date(jdf).sort_values(["No date flag","Date published"], ascending=[True,True])

                    with st.expander("Click to expand", expanded=True):
                        if len(journals) == 1:
                            st.markdown(f"#### Selected Journal: {journals[0]}")
                        else:
                            st.markdown("#### Selected Journals: " + ", ".join(journals))

                        cj1, cj2, cj3, cj4 = st.columns(4)
                        with cj1: c_m = st.container()
                        with cj2:
                            with st.popover("More metrics"):
                                c_cit      = st.container()
                                c_oa       = st.container()
                                c_collab   = st.container()
                                c_auth_no  = st.container()
                                c_auth_rat = st.container()
                                c_jcit_df  = st.container()
                        with cj3:
                            with st.popover("Relevant themes"):
                                st.markdown("##### Top 5 relevant themes")
                                fdc  = pd.merge(df_duplicated, jdf[["Zotero link"]], on="Zotero link")
                                fdc  = fdc[["Zotero link","Collection_Key","Collection_Name","Collection_Link"]]
                                fdc2 = fdc["Collection_Name"].value_counts().reset_index().head(10)
                                fdc2.columns = ["Collection_Name","Number_of_Items"]
                                fdc2 = fdc2[fdc2["Collection_Name"] != "01 Intelligence history"]
                                fdc  = pd.merge(fdc2, fdc, on="Collection_Name", how="left").drop_duplicates("Collection_Name").reset_index(drop=True)
                                fdc["Collection_Name"] = fdc["Collection_Name"].apply(remove_numbers)
                                for i, row in fdc.iterrows():
                                    st.caption(f"{i+1}) [{row['Collection_Name']}]({row['Collection_Link']}) {row['Number_of_Items']} items")
                        with cj4:
                            with st.popover("Filters and more"):
                                c_dl = st.container()
                                view = st.radio("View as:", ("Basic list","Table","Bibliography"), horizontal=True)

                        render_metrics(jdf, container_metric=c_m, container_citation=c_cit,
                                       container_citation_average=st.container(),
                                       container_oa=c_oa, container_author_no=c_auth_no,
                                       container_author_pub_ratio=c_auth_rat,
                                       container_publication_ratio=c_collab)

                        if len(journals) > 1:
                            c_jcit_df.dataframe(jdf.groupby("Journal")["Citation"].sum())

                        csv = convert_df_to_csv(
                            jdf[["Publication type","Title","Abstract","Date published",
                                 "Publisher","Journal","Link to publication","Zotero link","Citation"]]
                            .assign(Abstract=lambda d: d["Abstract"].str.replace("\n"," "))
                            .reset_index(drop=True)
                        )
                        c_dl.download_button(
                            "Download", csv,
                            f"selected_journal_{datetime.date.today().isoformat()}.csv",
                            mime="text/csv", key="dl-journal", icon=":material/download:",
                        )

                        on = st.toggle(":material/monitoring: Generate report")
                        if on and len(jdf):
                            st.info(f"Report for {journals}")
                            non_nan_id = jdf["ID"].count()
                            if non_nan_id != 0:
                                citation_count = jdf["Citation"].sum()
                                num_items      = len(jdf)
                                colcite1, colcite2, colcite3 = st.columns(3)
                                with colcite1:
                                    st.metric(label="Citation average", value=round(citation_count / num_items))
                                with colcite2:
                                    st.metric(label="Citation median", value=round(jdf["Citation"].median()))
                                with colcite3:
                                    st.metric(label="First citation occurence (avg year)",
                                              value=round(jdf["Year_difference"].mean()))
                            render_report_charts(jdf, str(journals), name_replacements,
                                                 show_themes=True, themes_df=fdc)
                            jdf_copy = jdf.copy()
                            jdf_copy["Year"] = pd.to_datetime(jdf_copy["Date published"]).dt.year
                            pub_by_year = jdf_copy.groupby(["Year","Journal"]).size().unstack().fillna(0).cumsum()
                            st.plotly_chart(px.line(pub_by_year, x=pub_by_year.index, y=pub_by_year.columns,
                                                    title="Cumulative Publications Over Years"),
                                            use_container_width=True)
                            if len(journals) > 1:
                                jcit = jdf.groupby("Journal")["Citation"].sum().reset_index()
                                jcit = jcit[jcit["Citation"] > 0].sort_values("Citation", ascending=False)
                                st.plotly_chart(px.bar(jcit, x="Journal", y="Citation",
                                                       title="Citations per Journal"), use_container_width=True)
                        else:
                            jdf = sort_radio(jdf, key="journal_sort")
                            if len(jdf) > 20 and st.checkbox("Show only first 20 items (untick to see all)", value=True):
                                jdf = jdf.head(20)
                            if view == "Basic list":
                                for i, row in jdf.iterrows():
                                    st.write(f"{i+1}) {format_entry(row)}")
                            elif view == "Table":
                                st.dataframe(
                                    jdf[["Publication type","Title","Journal","Date published","FirstName2",
                                         "Abstract","Link to publication","Zotero link"]]
                                    .rename(columns={"FirstName2":"Author(s)","Link to publication":"Publication link"})
                                )
                            elif view == "Bibliography":
                                jdf["zotero_item_key"] = jdf["Zotero link"].str.replace(
                                    "https://www.zotero.org/groups/intelarchive_intelligence_studies_database/items/","")
                                df_zot = pd.read_csv("zotero_citation_format.csv")
                                display_bibliographies(pd.merge(jdf, df_zot, on="zotero_item_key", how="left"))

                search_journal()

            # ================================================================
            # 5 – PUBLICATION YEAR
            # ================================================================
            elif search_option == 5:
                st.query_params.clear()
                st.subheader("Items by publication year", anchor=False, divider="blue")

                @st.fragment
                def search_pub_year():
                    reviews_map = load_reviews_map()
                    with st.expander("Click to expand", expanded=True):
                        df_all = df_dedup.copy()
                        df_all["Date published"] = parse_date_column(df_all["Date published"])
                        df_all["Date year"]      = pd.to_numeric(df_all["Date published"].str[:4], errors="coerce")
                        numeric_years = df_all["Date year"].dropna()
                        min_y, max_y  = int(numeric_years.min()), int(numeric_years.max())
                        df_all["Date published"] = df_all["Date published"].fillna("")
                        df_all = sort_by_date(df_all).sort_values("Date published", ascending=False)

                        current_year = date.today().year
                        years = st.slider("Publication years between:", min_y, max_y,
                                          (current_year, current_year + 1), key="years")
                        df_all = df_all[(df_all["Date year"] >= years[0]) & (df_all["Date year"] <= years[1])]

                        cy1, cy2, cy3, cy4 = st.columns(4)
                        with cy1: c_m = st.container()
                        with cy2:
                            with st.popover("More metrics"):
                                c_cit      = st.container()
                                c_cit_avg  = st.container()
                                c_oa       = st.container()
                                c_type     = st.container()
                                c_auth_no  = st.container()
                                c_auth_rat = st.container()
                                c_collab   = st.container()
                        with cy3:
                            with st.popover("Relevant themes"):
                                st.markdown("##### Top relevant themes")
                                c_themes = st.container()
                        with cy4:
                            with st.popover("Filters and more"):
                                st.warning("Items without a publication date are not listed here!")
                                sel_types = st.multiselect("Filter by publication type:", df_all["Publication type"].unique())
                                if sel_types:
                                    df_all = df_all[df_all["Publication type"].isin(sel_types)]
                                df_all = df_all.reset_index(drop=True)
                                c_dl = st.container()
                                view = st.radio("View as:", ("Basic list","Table","Bibliography"), horizontal=True)

                        render_metrics(df_all, container_metric=c_m, container_citation=c_cit,
                                       container_citation_average=c_cit_avg, container_oa=c_oa,
                                       container_type=c_type, container_author_no=c_auth_no,
                                       container_author_pub_ratio=c_auth_rat,
                                       container_publication_ratio=c_collab,
                                       label=f"#Sources {years[0]}-{years[1]}")

                        fdc  = pd.merge(df_duplicated, df_all[["Zotero link"]], on="Zotero link")
                        fdc  = fdc[["Zotero link","Collection_Key","Collection_Name","Collection_Link"]]
                        fdc2 = fdc["Collection_Name"].value_counts().reset_index().head(10)
                        fdc2.columns = ["Collection_Name","Number_of_Items"]
                        fdc2 = fdc2[fdc2["Collection_Name"] != "01 Intelligence history"]
                        fdc  = pd.merge(fdc2, fdc, on="Collection_Name", how="left").drop_duplicates("Collection_Name").reset_index(drop=True)
                        fdc["Collection_Name"] = fdc["Collection_Name"].apply(remove_numbers)
                        for i, row in fdc.iterrows():
                            c_themes.caption(f"{i+1}) [{row['Collection_Name']}]({row['Collection_Link']}) {row['Number_of_Items']} items")

                        csv = convert_df_to_csv(
                            df_all[["Publication type","Title","Abstract","FirstName2",
                                    "Link to publication","Zotero link","Date published","Citation"]]
                            .rename(columns={"FirstName2":"Author(s)"})
                            .assign(Abstract=lambda d: d["Abstract"].str.replace("\n"," "))
                        )
                        label_str = f"{years[0]}-{years[1]}"
                        c_dl.download_button(
                            "Download selected items", csv,
                            f"intelligence-bibliography-items-between-{label_str}.csv",
                            mime="text/csv", key="dl-year", icon=":material/download:",
                        )

                        on = st.toggle(":material/monitoring: Generate report")
                        if on and len(df_all):
                            st.info(f"Report for {label_str}")
                            render_report_charts(df_all, label_str, name_replacements,
                                                 show_themes=True, themes_df=fdc)
                        else:
                            df_all = sort_radio(df_all, key="year_sort")
                            if len(df_all) > 20 and st.checkbox("Show only first 20 items (untick to see all)", value=True, key="all_items"):
                                df_all = df_all.head(20)
                            if view == "Basic list":
                                articles  = [format_entry(row, include_citation=True, reviews_map=reviews_map) for _, row in df_all.iterrows()]
                                abstracts = [row["Abstract"] if pd.notnull(row["Abstract"]) else "N/A" for _, row in df_all.iterrows()]
                                render_paginated_list(df_all, articles, abstracts)
                            elif view == "Table":
                                st.dataframe(
                                    df_all[["Publication type","Title","Date published","FirstName2",
                                            "Abstract","Link to publication","Zotero link"]]
                                    .rename(columns={"FirstName2":"Author(s)","Link to publication":"Publication link"})
                                )
                            elif view == "Bibliography":
                                df_all["zotero_item_key"] = df_all["Zotero link"].str.replace(
                                    "https://www.zotero.org/groups/intelarchive_intelligence_studies_database/items/","")
                                df_zot = pd.read_csv("zotero_citation_format.csv")
                                display_bibliographies(pd.merge(df_all, df_zot, on="zotero_item_key", how="left"))

                search_pub_year()

            # ================================================================
            # 6 – CITED PAPERS
            # ================================================================
            elif search_option == 6:
                st.query_params.clear()
                st.subheader("Cited items in the library", anchor=False, divider="blue")

                @st.fragment
                def search_cited_papers():
                    reviews_map = load_reviews_map()
                    with st.expander("Click to expand", expanded=True):
                        c_md              = st.container()
                        df_cited          = df_dedup[df_dedup["Citation"].notna()].copy().reset_index(drop=True)
                        df_cited_for_mean = df_dedup.copy()
                        non_nan_id        = df_dedup["ID"].count()

                        cc1, cc2, cc3 = st.columns(3)
                        with cc1: c_m = st.container()
                        with cc2:
                            with st.popover("More metrics"):
                                c_cit      = st.container()
                                c_cit_avg  = st.container()
                                c_oa       = st.container()
                                c_auth_no  = st.container()
                                c_auth_rat = st.container()
                                c_collab   = st.container()
                        with cc3:
                            with st.popover("Filters and more"):
                                st.warning("Citation data from [OpenAlex](https://openalex.org/).")
                                citation_type = st.radio(
                                    "Select:", ("All citations","Trends","Citations without outliers"), horizontal=True,
                                )
                                c_slider = st.container()
                                c_dl     = st.container()
                                view     = st.radio("View as:", ("Basic list","Table","Bibliography"), horizontal=True)

                        c_md.markdown(f"#### {citation_type}")
                        current_year = datetime.datetime.now().year

                        if citation_type == "Trends":
                            df_cited = df_cited[
                                (df_cited["Last_citation_year"].isin([current_year, current_year-1])) &
                                (df_cited["Publication_year"].isin([current_year, current_year-1]))
                            ]
                        elif citation_type == "Citations without outliers":
                            df_cited          = df_cited[df_cited["Citation"] < 1000]
                            df_cited_for_mean = df_cited_for_mean[df_cited_for_mean["Citation"] < 1000]

                        max_cit   = int(df_cited["Citation"].max()) if len(df_cited) else 1
                        sel_range = c_slider.slider("Select a citation range:", 1, max_cit, (1, max_cit))
                        df_cited  = df_cited[(df_cited["Citation"] >= sel_range[0]) & (df_cited["Citation"] <= sel_range[1])]

                        df_cited["Date published"] = parse_date_column(df_cited["Date published"])
                        df_cited["Date published"] = df_cited["Date published"].fillna("")
                        df_cited = sort_by_date(df_cited).sort_values("Date published", ascending=False).reset_index(drop=True)

                        render_metrics(df_cited, container_metric=c_m, container_citation=c_cit,
                                       container_citation_average=c_cit_avg, container_oa=c_oa,
                                       container_author_no=c_auth_no, container_author_pub_ratio=c_auth_rat,
                                       container_publication_ratio=c_collab,
                                       label="Number of cited publications")

                        if citation_type == "Trends":
                            st.info(f"Shows citations in {current_year-1}-{current_year} to papers from the same period.")
                        elif citation_type == "Citations without outliers":
                            outlier_count = int((df_dedup["Citation"] > 1000).sum())
                            st.info(f"**{outlier_count}** items with >1000 citations are excluded.")

                        csv = convert_df_to_csv(
                            df_cited[["Publication type","Title","Abstract","FirstName2",
                                      "Link to publication","Zotero link","Date published","Citation"]]
                            .rename(columns={"FirstName2":"Author(s)"})
                            .assign(Abstract=lambda d: d["Abstract"].str.replace("\n"," "))
                        )
                        c_dl.download_button(
                            "Download selected items", csv, "cited-items.csv",
                            mime="text/csv", key="dl-cited", icon=":material/download:",
                        )

                        on = st.toggle(":material/monitoring: Generate report")
                        if on and len(df_cited):
                            st.markdown("#### Report for cited items in the library")
                            non_nan_c       = df_cited.dropna(subset=["Citation_list"])
                            citation_mean   = non_nan_c["Citation"].mean()
                            citation_median = non_nan_c["Citation"].median()
                            colcite1, colcite2, colcite3 = st.columns(3)
                            with colcite1:
                                st.metric(label="Citation average", value=round(citation_mean, 2))
                            with colcite2:
                                st.metric(label="Citation median", value=round(citation_median, 2))
                            with colcite3:
                                mean_first = df_cited["Year_difference"].mean()
                                st.metric(label="First citation occurence (avg year)", value=round(mean_first))

                            citation_dist = df_cited["Citation"].value_counts().sort_index().reset_index()
                            citation_dist.columns = ["Number of Citations","Number of Articles"]
                            fig = px.scatter(citation_dist, x="Number of Citations", y="Number of Articles",
                                             title="Distribution of Citations Across Articles")
                            fig.update_traces(marker=dict(color="red", size=7, opacity=0.5))
                            st.plotly_chart(fig)

                            fig2 = go.Figure(data=go.Scatter(
                                x=df_cited["Year_difference"], y=[0]*len(df_cited), mode="markers"))
                            fig2.update_layout(title="First citation occurence (years after publication)",
                                               xaxis_title="Year Difference", yaxis_title="")
                            st.plotly_chart(fig2)

                            render_report_charts(df_cited, "cited items", name_replacements)
                        else:
                            df_cited = sort_radio(df_cited, key="cited_sort")
                            if len(df_cited) > 20 and st.checkbox("Show only first 20 items (untick to see all)", value=True, key="all_items"):
                                df_cited = df_cited.head(20)
                            if view == "Basic list":
                                for i, row in df_cited.iterrows():
                                    st.markdown(f"{i+1}. {format_entry(row, include_citation=True, reviews_map=reviews_map)}", unsafe_allow_html=True)
                            elif view == "Table":
                                st.dataframe(
                                    df_cited[["Publication type","Title","Date published","FirstName2",
                                              "Abstract","Journal","Link to publication","Zotero link","Citation"]]
                                    .rename(columns={"FirstName2":"Author(s)","Link to publication":"Publication link"})
                                )
                            elif view == "Bibliography":
                                df_cited["zotero_item_key"] = df_cited["Zotero link"].str.replace(
                                    "https://www.zotero.org/groups/intelarchive_intelligence_studies_database/items/","")
                                df_zot = pd.read_csv("zotero_citation_format.csv")
                                display_bibliographies(pd.merge(df_cited, df_zot, on="zotero_item_key", how="left"))

                search_cited_papers()

            # ── Overview ────────────────────────────────────────────────────
            st.header("Overview", anchor=False)

            @st.fragment
            def overview():
                tab11, tab12, tab13 = st.tabs(["Recently added items","Recently published items","Top cited items"])

                with tab11:
                    st.markdown("#### Recently added or updated items")
                    reviews_map = load_reviews_map()
                    df_ov = df_dedup.sort_values("Date added", ascending=False).head(10).copy()
                    df_ov["Date published"] = parse_date_column(df_ov["Date published"], fmt="%d-%m-%Y")
                    df_ov["Date published"] = df_ov["Date published"].fillna("No date")
                    df_ov["Abstract"]       = df_ov["Abstract"].fillna("No abstract")
                    display = st.checkbox("Display abstract")
                    for i, row in df_ov.iterrows():
                        st.markdown(f"{i+1}) {format_entry(row, include_citation=True, reviews_map=reviews_map)}", unsafe_allow_html=True)
                        if display and row["Abstract"]:
                            st.markdown(f"**Abstract:** {row['Abstract']}")

                with tab12:
                    st.markdown("#### Recently published items")
                    display2 = st.checkbox("Display abstracts", key="recently_published")
                    df_ov2   = df_dedup.copy()
                    df_ov2["Date published"] = pd.to_datetime(df_ov2["Date published"], utc=True, errors="coerce").dt.tz_convert("Europe/London")
                    now      = datetime.datetime.now(datetime.timezone.utc).astimezone(datetime.timezone(datetime.timedelta(hours=1)))
                    df_ov2   = df_ov2[df_ov2["Date published"] <= now]
                    df_ov2["Date published"] = df_ov2["Date published"].dt.strftime("%Y-%m-%d").fillna("")
                    df_ov2   = df_ov2.sort_values("Date published", ascending=False).head(10).reset_index(drop=True)
                    for i, row in df_ov2.iterrows():
                        st.write(f"{i+1}) {format_entry(row, include_citation=True)}")
                        if display2:
                            st.caption(row["Abstract"])

                with tab13:
                    st.markdown("#### Top cited items")
                    display3 = st.checkbox("Display abstracts", key="top_cited")

                    @st.cache_resource(ttl=5000)
                    def _top_cited():
                        df_t = df_dedup.copy()
                        df_t["Date published"] = parse_date_column(df_t["Date published"])
                        return df_t.sort_values("Citation", ascending=False).reset_index(drop=True)

                    df_top = _top_cited().head(10)
                    for i, row in df_top.iterrows():
                        st.write(f"{i+1}) {format_entry(row)}")
                        if display3:
                            st.caption(row["Abstract"])

            overview()

            # ── All items ───────────────────────────────────────────────────
            st.header("All items in database", anchor=False)
            with st.expander("Click to expand", expanded=False):
                st.write("""
                The entire dataset is available on Zenodo (updated quarterly):

                Ozkan, Yusuf A. 'Intelligence Studies Network Dataset'. Zenodo, 15 August 2024.
                https://doi.org/10.5281/zenodo.13325698.
                """)
                df_added = df_dedup.copy()
                df_added["Date added"]  = pd.to_datetime(df_added["Date added"])
                df_added["YearMonth"]   = df_added["Date added"].dt.to_period("M").astype(str)
                monthly    = df_added.groupby("YearMonth").size().rename("Number of items added")
                cumulative = monthly.cumsum()
                chart = (
                    alt.Chart(pd.DataFrame({"YearMonth": cumulative.index, "Total items": cumulative}))
                    .mark_bar()
                    .encode(x="YearMonth", y="Total items", tooltip=["YearMonth","Total items"])
                    .properties(width=500, height=600, title="Total Number of Items Added")
                )
                st.subheader("Growth of the library", anchor=False, divider="blue")
                st.altair_chart(chart, use_container_width=True)

        # ── Right sidebar col ───────────────────────────────────────────────
        with col2:
            st.info("Join the [mailing list](https://groups.google.com/g/intelarchive)")

            @st.fragment
            def collection_buttons():
                pages = [
                    ("Intelligence history",              "pages/1_Intelligence history.py"),
                    ("Intelligence studies",              "pages/2_Intelligence studies.py"),
                    ("Intelligence analysis",             "pages/3_Intelligence analysis.py"),
                    ("Intelligence organisations",        "pages/4_Intelligence organisations.py"),
                    ("Intelligence failures",             "pages/5_Intelligence failures.py"),
                    ("Intelligence oversight and ethics", "pages/6_Intelligence oversight and ethics.py"),
                    ("Intelligence collection",           "pages/7_Intelligence collection.py"),
                    ("Counterintelligence",               "pages/8_Counterintelligence.py"),
                    ("Covert action",                     "pages/9_Covert action.py"),
                    ("Intelligence and cybersphere",      "pages/10_Intelligence and cybersphere.py"),
                    ("Global intelligence",               "pages/11_Global intelligence.py"),
                    ("Special collections",               "pages/12_Special collections.py"),
                ]
                with st.expander("Collections", expanded=True):
                    for label, page in pages:
                        if st.button(label):
                            st.switch_page(page)

            collection_buttons()

            with st.expander("Events & conferences", expanded=True):
                for info in evens_conferences():
                    st.write(info)

            with st.expander("Digest", expanded=True):
                st.write("See our dynamic [digest](https://intelligence.streamlit.app/Digest) for the latest updates!")

    # ════════════════════════════════════════════════════════════════════════
    # TAB 2 – DASHBOARD
    # ════════════════════════════════════════════════════════════════════════
    with tab2:
        st.header("Dashboard", anchor=False)
        on_main_dashboard = st.toggle(":material/dashboard: Display dashboard")

        if on_main_dashboard:
            df_csv           = df_duplicated.copy()
            df_collections_2 = df_csv.copy()
            df_csv           = df_dedup.copy().reset_index(drop=True)

            df_csv["Date published"] = parse_date_column(df_csv["Date published"])
            df_csv["Date year"]      = df_csv["Date published"].str[:4].fillna("No date")

            df_year = df_csv["Date year"].value_counts().reset_index()
            df_year.columns = ["Publication year","Count"]
            df_year.drop(df_year[df_year["Publication year"] == "No date"].index, inplace=True)
            df_year = df_year.sort_values("Publication year").reset_index(drop=True)
            max_y   = int(df_year["Publication year"].max())
            min_y   = int(df_year["Publication year"].min())

            df_collections_2["Date published"] = parse_date_column(df_collections_2["Date published"])
            df_collections_2["Date year"]      = df_collections_2["Date published"].str[:4].fillna("No date")

            with st.expander("**Select filters**", expanded=False):
                types = st.multiselect("Publication type",
                                       df_csv["Publication type"].unique(),
                                       df_csv["Publication type"].unique())
                df_journals_dash = df_dedup[df_dedup["Publication type"] == "Journal article"]
                journals_dash    = st.multiselect("Select a journal",
                                                  df_journals_dash["Journal"].value_counts().index.tolist(),
                                                  key="big_dashboard_journals")
                years = st.slider("Publication years between:", min_y, max_y + 1, (min_y, max_y + 1), key="years2")

                if st.button("Update dashboard"):
                    df_csv = df_csv[df_csv["Publication type"].isin(types)]
                    if journals_dash:
                        df_csv = df_csv[df_csv["Journal"].isin(journals_dash)]
                    df_csv = df_csv[df_csv["Date year"] != "No date"]
                    df_csv = df_csv[(df_csv["Date year"].astype(int) >= years[0]) &
                                    (df_csv["Date year"].astype(int) < years[1])]
                    df_year = df_csv["Date year"].value_counts().reset_index()
                    df_year.columns = ["Publication year","Count"]
                    df_year.drop(df_year[df_year["Publication year"] == "No date"].index, inplace=True)
                    df_year = df_year.sort_values("Publication year").reset_index(drop=True)

                    df_collections_2 = df_collections_2[df_collections_2["Publication type"].isin(types)]
                    if journals_dash:
                        df_collections_2 = df_collections_2[df_collections_2["Journal"].isin(journals_dash)]
                    df_collections_2 = df_collections_2[df_collections_2["Date year"] != "No date"]
                    df_collections_2 = df_collections_2[
                        (df_collections_2["Date year"].astype(int) >= years[0]) &
                        (df_collections_2["Date year"].astype(int) < years[1])
                    ]

            if not df_csv["Title"].any():
                st.warning("No data to visualise. Select a correct parameter.")
            else:
                # ── Collections ────────────────────────────────────────────
                st.subheader("Publications by collection", anchor=False, divider="blue")

                @st.fragment
                def collection_chart():
                    df_col21 = df_collections_2["Collection_Name"].value_counts().reset_index()
                    df_col21.columns = ["Collection_Name","Number_of_Items"]

                    col1, col2 = st.columns(2)
                    with col1:
                        colallcol1, colallcol2 = st.columns([2, 3])
                        with colallcol1:
                            show_legend = st.checkbox("Show legend", key="collection_bar_legend_check")
                            last_5_col  = st.checkbox("Limit to last 5 years", key="last5yearscollections")
                            if last_5_col:
                                df_col21 = df_collections_2[df_collections_2["Date year"] != "No date"].copy()
                                df_col21["Date year"] = df_col21["Date year"].astype(int)
                                df_col21 = df_col21[df_col21["Date year"] > (datetime.datetime.now().year - 5)]
                                df_col21 = df_col21["Collection_Name"].value_counts().reset_index()
                                df_col21.columns = ["Collection_Name","Number_of_Items"]
                        with colallcol2:
                            number0 = st.slider("Select a number of collections", 3, len(df_col21), 10, key="slider01")
                        plot = df_col21.head(number0 + 1)
                        plot = plot[plot["Collection_Name"] != "01 Intelligence history"]
                        fig  = px.bar(plot, x="Collection_Name", y="Number_of_Items", color="Collection_Name")
                        fig.update_xaxes(tickangle=-65)
                        fig.update_traces(width=0.6)
                        fig.update_layout(autosize=False, width=600, height=600, showlegend=show_legend,
                                          title=f"Top {number0} collections in the library")
                        st.plotly_chart(fig, use_container_width=True)

                    with col2:
                        colcum1, colcum2, colcum3 = st.columns(3)
                        with colcum1: hide_legend = st.checkbox("Hide legend", key="collection_line_legend_check")
                        with colcum2: last_5_cum  = st.checkbox("Limit to last 5 years", key="last5yearscollectioncummulative")
                        with colcum3: top_5_only  = st.checkbox("Show top 5 collections", key="top5collections")

                        df_col22 = df_collections_2.copy()
                        if last_5_cum:
                            df_col22 = df_col22[df_col22["Date year"] != "No date"].copy()
                            df_col22["Date year"] = df_col22["Date year"].astype(int)
                            df_col22 = df_col22[df_col22["Date year"] > (datetime.datetime.now().year - 5)]

                        col_counts = df_col22.groupby(["Date year","Collection_Name"]).size().unstack().fillna(0)
                        col_counts = col_counts.reset_index()
                        col_counts.iloc[:, 1:] = col_counts.iloc[:, 1:].cumsum()
                        top_cols   = df_col22["Collection_Name"].value_counts().head(5).index.tolist() if top_5_only \
                                     else df_col22["Collection_Name"].unique().tolist()
                        col_filt   = col_counts[["Date year"] + top_cols]
                        col_filt["Date year"] = pd.to_numeric(col_filt["Date year"], errors="coerce")
                        col_filt   = col_filt.sort_values("Date year")
                        fig = px.line(col_filt, x="Date year", y=top_cols, markers=True,
                                      title="Cumulative changes in collection over years")
                        fig.update_layout(showlegend=not hide_legend)
                        st.plotly_chart(fig, use_container_width=True)

                collection_chart()

                st.divider()
                st.subheader("Publications by type and year", anchor=False, divider="blue")

                @st.fragment
                def types_pubyears():
                    df_types   = df_csv["Publication type"].value_counts().reset_index()
                    df_types.columns = ["Publication type","Count"]
                    chart_type = st.radio("Choose visual type", ["Bar chart","Pie chart"], horizontal=True)

                    col1, col2 = st.columns(2)
                    with col1:
                        coltype1, coltype2 = st.columns(2)
                        with coltype1:
                            last_5_types = st.checkbox("Limit to last 5 years", key="last5yearsitemtypes")
                        with coltype2:
                            log0 = st.checkbox("Show in log scale", key="log0", disabled=(chart_type == "Pie chart"))
                        if last_5_types:
                            df_csv2 = df_csv[df_csv["Date year"] != "No date"].copy()
                            df_csv2["Date year"] = df_csv2["Date year"].astype(int)
                            df_csv2 = df_csv2[df_csv2["Date year"] > (datetime.datetime.now().year - 5)]
                            df_types = df_csv2["Publication type"].value_counts().reset_index()
                            df_types.columns = ["Publication type","Count"]
                        if chart_type == "Bar chart":
                            fig = px.bar(df_types, x="Publication type", y="Count", color="Publication type",
                                         log_y=log0, title="Item types" + (" (log scale)" if log0 else ""))
                            fig.update_traces(width=0.6)
                            fig.update_xaxes(tickangle=-70)
                            st.plotly_chart(fig, use_container_width=True)
                        else:
                            fig = px.pie(df_types, values="Count", names="Publication type", title="Item types")
                            st.plotly_chart(fig, use_container_width=True)

                    with col2:
                        coly1, coly2 = st.columns(2)
                        df_year_dash = df_year.copy()
                        df_year_dash["Publication year"] = df_year_dash["Publication year"].astype(int)
                        with coly1:
                            last_10 = st.checkbox("Limit to last 10 years", value=False)
                            if last_10:
                                cur = datetime.datetime.now().year
                                df_year_dash = df_year_dash[df_year_dash["Publication year"] >= cur - 9]
                        with coly2:
                            min_yr = int(df_year_dash["Publication year"].min())
                            max_yr = int(df_year_dash["Publication year"].max())
                            if min_yr == max_yr:
                                st.warning(f"All publications are from {min_yr}.")
                                yr_range = (min_yr, max_yr)
                            else:
                                yr_range = st.slider("Publication years:", min_yr, max_yr, (min_yr, max_yr), key="years3")
                        df_year_dash = df_year_dash[(df_year_dash["Publication year"] >= yr_range[0]) &
                                                    (df_year_dash["Publication year"] <= yr_range[1])]
                        if not df_year_dash.empty:
                            fig = px.bar(df_year_dash, x="Publication year", y="Count",
                                         title=f"All items by publication year {yr_range[0]}-{yr_range[1]}")
                            fig.update_xaxes(tickangle=-70, type="category")
                            st.plotly_chart(fig, use_container_width=True)

                types_pubyears()

                st.divider()
                st.subheader("Publications by author", anchor=False, divider="blue")

                @st.fragment
                def author_chart():
                    df_auth  = df_csv.copy()
                    df_auth2 = df_csv.copy()
                    num_authors = st.slider("Select number of authors to display:", 5, 30, 20, key="author2")

                    col1, col2 = st.columns(2)
                    with col1:
                        colauth1, colauth2 = st.columns(2)
                        with colauth1:
                            table_view = st.radio("Choose visual type", ["Bar chart","Table view"], key="author", horizontal=True)
                        with colauth2:
                            last_5_auth = st.checkbox("Limit to last 5 years", key="last5yearsauthorsall")
                        if last_5_auth:
                            df_auth = df_csv[df_csv["Date year"] != "No date"].copy()
                            df_auth["Date year"] = df_auth["Date year"].astype(int)
                            df_auth = df_auth[df_auth["Date year"] > (datetime.datetime.now().year - 5)]
                        df_auth_exp = df_auth.copy()
                        df_auth_exp["Author_name"] = df_auth_exp["FirstName2"].apply(
                            lambda x: x.split(", ") if isinstance(x, str) and x else [])
                        df_auth_exp = df_auth_exp.explode("Author_name")
                        df_auth_exp["Author_name"] = df_auth_exp["Author_name"].map(name_replacements).fillna(df_auth_exp["Author_name"])
                        df_auth_exp = df_auth_exp[df_auth_exp["Author_name"] != "nan"]
                        top_auth    = df_auth_exp["Author_name"].value_counts().head(num_authors).reset_index()
                        top_auth.columns = ["Author","Number of Publications"]
                        if table_view == "Bar chart":
                            fig = px.bar(top_auth, x="Author", y="Number of Publications",
                                         title=f"Top {num_authors} Authors (all items)")
                            fig.update_layout(xaxis_tickangle=-45)
                            st.plotly_chart(fig)
                        else:
                            st.markdown(f"###### Top {num_authors} Authors (all items)")
                            st.dataframe(top_auth.rename(columns={"Author":"Author name","Number of Publications":"Publication count"}))

                    with col2:
                        colauth11, colauth12 = st.columns(2)
                        with colauth11:
                            sel_type_auth = st.radio("Select a publication type",
                                                     ["Journal article","Book","Book chapter"], horizontal=True)
                        with colauth12:
                            last_5_auth2 = st.checkbox("Limit to last 5 years", key="last5yearsauthorsallspecified")
                        df_auth_t = df_csv[df_csv["Publication type"] == sel_type_auth].copy()
                        if last_5_auth2:
                            df_auth_t = df_auth_t[df_auth_t["Date year"] != "No date"]
                            df_auth_t["Date year"] = df_auth_t["Date year"].astype(int)
                            df_auth_t = df_auth_t[df_auth_t["Date year"] > (datetime.datetime.now().year - 5)]
                        if len(df_auth_t):
                            df_auth_t["Author_name"] = df_auth_t["FirstName2"].apply(
                                lambda x: x.split(", ") if isinstance(x, str) and x else [])
                            df_auth_t = df_auth_t.explode("Author_name")
                            df_auth_t["Author_name"] = df_auth_t["Author_name"].map(name_replacements).fillna(df_auth_t["Author_name"])
                            df_auth_t = df_auth_t[df_auth_t["Author_name"] != "nan"]
                            top_t = df_auth_t["Author_name"].value_counts().head(num_authors).reset_index()
                            top_t.columns = ["Author","Number of Publications"]
                            if table_view == "Bar chart":
                                fig = px.bar(top_t, x="Author", y="Number of Publications",
                                             title=f"Top {num_authors} Authors ({sel_type_auth})")
                                fig.update_layout(xaxis_tickangle=-45)
                                st.plotly_chart(fig)
                            else:
                                st.markdown(f"###### Top {num_authors} Authors ({sel_type_auth})")
                                st.dataframe(top_t.rename(columns={"Author":"Author name","Number of Publications":"Publication count"}))
                        else:
                            st.write("No data to visualize")

                    st.markdown("##### Single vs Multiple authored publications",
                                help="Theses excluded as they are inherently single-authored.")
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        df_auth2["multiple_authors"] = df_auth2["FirstName2"].apply(
                            lambda x: isinstance(x, str) and "," in x)
                        df_auth3  = df_auth2[df_auth2["Publication type"] != "Thesis"].copy()
                        grouped3  = df_auth3.groupby("Date year")
                        total3    = grouped3.size().reset_index(name="Total Publications")
                        multi3    = grouped3["multiple_authors"].apply(lambda x: (x==True).sum()).reset_index(name="# Multiple Authored Publications")
                        df_multi3 = pd.merge(total3, multi3, on="Date year")
                        df_multi3["# Single Authored Publications"] = df_multi3["Total Publications"] - df_multi3["# Multiple Authored Publications"]

                        df_auth2["Date year"] = pd.to_numeric(df_auth2["Date year"], errors="coerce")
                        grouped   = df_auth2.groupby("Date year")
                        total     = grouped.size().reset_index(name="Total Publications")
                        multi     = grouped["multiple_authors"].apply(lambda x: (x==True).sum()).reset_index(name="# Multiple Authored Publications")
                        df_multi  = pd.merge(total, multi, on="Date year")
                        df_multi["# Single Authored Publications"]      = df_multi["Total Publications"] - df_multi["# Multiple Authored Publications"]
                        df_multi["% Multiple Authored Publications"]    = round(df_multi["# Multiple Authored Publications"] / df_multi["Total Publications"], 3) * 100
                        df_multi["% Single Authored Publications"]      = 100 - df_multi["% Multiple Authored Publications"]
                        df_multi  = df_multi[df_multi["Date year"] <= datetime.datetime.now().year]
                        last_20   = df_multi[df_multi["Date year"] >= (df_multi["Date year"].max() - 20)]

                        see_number = st.toggle("See number of publications")
                        fig1 = go.Figure()
                        fig1.add_trace(go.Scatter(x=last_20["Date year"], y=last_20["# Multiple Authored Publications"],
                                                  mode="lines+markers", name="# Multiple Authored", line=dict(color="goldenrod")))
                        fig1.add_trace(go.Scatter(x=last_20["Date year"], y=last_20["# Single Authored Publications"],
                                                  mode="lines+markers", name="# Single Authored", line=dict(color="green")))
                        fig1.update_layout(title="# Single vs Multiple Authored Publications",
                                           xaxis_title="Year", yaxis_title="Number of Publications")
                        fig2 = go.Figure()
                        fig2.add_trace(go.Scatter(x=last_20["Date year"], y=last_20["% Multiple Authored Publications"],
                                                  mode="lines+markers", name="% Multiple Authored", line=dict(color="goldenrod")))
                        fig2.add_trace(go.Scatter(x=last_20["Date year"], y=last_20["% Single Authored Publications"],
                                                  mode="lines+markers", name="% Single Authored", line=dict(color="green")))
                        fig2.update_layout(title="% Single vs Multiple Authored Publications",
                                           xaxis_title="Publication Year", yaxis_title="% Publications")
                        st.plotly_chart(fig1 if see_number else fig2, use_container_width=True)

                    with col2:
                        last_5_pie = st.checkbox("Limit to last 5 years", key="last5yearsauthor")
                        df_pie     = df_multi3.copy()
                        if last_5_pie:
                            df_pie = df_pie[df_pie["Date year"] >= (df_pie["Date year"].max() - 5)]
                        fig = px.pie(
                            values=[df_pie["# Multiple Authored Publications"].sum(),
                                    df_pie["# Single Authored Publications"].sum()],
                            names=["Multiple Authored","Single Authored"],
                            title="Single vs Multiple Authored Papers",
                            color_discrete_sequence=["goldenrod","green"],
                        )
                        st.plotly_chart(fig)

                author_chart()

                st.divider()
                st.subheader("Publishers and Journals", anchor=False, divider="blue")
                col1, col2 = st.columns(2)

                with col1:
                    @st.fragment
                    def publisher_chart():
                        number  = st.slider("Select a number of publishers", 0, 30, 10)
                        df_pub  = df_csv["Publisher"].value_counts().reset_index()
                        df_pub.columns = ["Publisher","Count"]
                        df_pub  = df_pub.sort_values("Count", ascending=False).head(number)
                        log1    = st.checkbox("Show in log scale", key="log1")
                        leg1    = st.checkbox("Disable legend", key="leg1")
                        tbl_pub = st.checkbox("Table view")
                        if tbl_pub:
                            st.dataframe(df_pub)
                        elif not df_pub.empty:
                            fig = px.bar(df_pub, x="Publisher", y="Count", color="Publisher", log_y=log1,
                                         title=f"Top {number} publishers" + (" (log scale)" if log1 else ""))
                            fig.update_traces(width=0.6)
                            fig.update_layout(autosize=False, width=1200, height=700, showlegend=not leg1)
                            fig.update_xaxes(tickangle=-70)
                            st.plotly_chart(fig, use_container_width=True)
                    publisher_chart()

                with col2:
                    @st.fragment
                    def journal_chart():
                        number2  = st.slider("Select a number of journals", 0, 30, 10)
                        df_jour  = df_csv[df_csv["Publication type"] == "Journal article"]["Journal"].value_counts().reset_index()
                        df_jour.columns = ["Journal","Count"]
                        df_jour  = df_jour.sort_values("Count", ascending=False).head(number2)
                        log2     = st.checkbox("Show in log scale", key="log2")
                        leg2     = st.checkbox("Disable legend", key="leg2")
                        tbl_jour = st.checkbox("Table view", key="journal")
                        if tbl_jour:
                            st.dataframe(df_jour)
                        elif not df_jour.empty:
                            fig = px.bar(df_jour, x="Journal", y="Count", color="Journal", log_y=log2,
                                         title=f"Top {number2} journals" + (" (log scale)" if log2 else ""))
                            fig.update_traces(width=0.6)
                            fig.update_layout(autosize=False, width=1200, height=700, showlegend=not leg2)
                            fig.update_xaxes(tickangle=-70)
                            st.plotly_chart(fig, use_container_width=True)
                    journal_chart()

                st.divider()
                st.subheader("Publications by open access status", anchor=False, divider="blue")

                df_dedup_oa = df_collections_2.drop_duplicates(subset="Zotero link").copy()
                df_dedup_oa["Date year"] = pd.to_numeric(df_dedup_oa["Date year"], errors="coerce")
                df_dedup_v2 = df_dedup_oa.dropna(subset=["OA status"]).copy()
                df_dedup_v2["Citation status"] = df_dedup_v2["Citation"].apply(
                    lambda x: False if pd.isna(x) or x == 0 else True)
                filtered_oa  = df_dedup_v2[(df_dedup_v2["Citation status"]) & (df_dedup_v2["OA status"] == True)]
                filtered_oa2 = df_dedup_v2[df_dedup_v2["Citation status"]]
                df_cited_oa  = filtered_oa.groupby("Date year")["OA status"].count().reset_index()
                df_cited_oa.columns = ["Date year","Cited OA papers"]

                @st.fragment
                def oa_charts():
                    df_cited_p = filtered_oa2.groupby("Date year")["OA status"].count().reset_index()
                    df_cited_p.columns = ["Date year","Cited papers"]
                    df_cited_p = pd.merge(df_cited_p, df_cited_oa, on="Date year", how="left")
                    df_cited_p["Cited OA papers"]     = df_cited_p["Cited OA papers"].fillna(0)
                    df_cited_p["Cited non-OA papers"] = df_cited_p["Cited papers"] - df_cited_p["Cited OA papers"]
                    df_cited_p["%Cited OA papers"]     = round(df_cited_p["Cited OA papers"] / df_cited_p["Cited papers"], 3) * 100
                    df_cited_p["%Cited non-OA papers"] = 100 - df_cited_p["%Cited OA papers"]

                    grouped_oa = df_dedup_v2.groupby("Date year")
                    total_oa   = grouped_oa.size().reset_index(name="Total Publications")
                    open_oa    = grouped_oa["OA status"].apply(lambda x: (x==True).sum()).reset_index(name="#OA Publications")
                    df_oa_time = pd.merge(total_oa, open_oa, on="Date year")
                    df_oa_time["#Non-OA Publications"]    = df_oa_time["Total Publications"] - df_oa_time["#OA Publications"]
                    df_oa_time["OA publication ratio"]    = round(df_oa_time["#OA Publications"] / df_oa_time["Total Publications"], 3) * 100
                    df_oa_time["Non-OA publication ratio"] = 100 - df_oa_time["OA publication ratio"]
                    df_oa_time = pd.merge(df_oa_time, df_cited_p, on="Date year")

                    col1, col2 = st.columns([3, 1])
                    with col1:
                        last_20_oa = df_oa_time[df_oa_time["Date year"] >= (df_oa_time["Date year"].max() - 20)]
                        cit_ratio  = st.checkbox("Add citation ratio")
                        fig = px.bar(last_20_oa, x="Date year",
                                     y=["OA publication ratio","Non-OA publication ratio"],
                                     title="Open Access Publications Ratio (last 20 years)",
                                     color_discrete_map={"OA publication ratio":"green","Non-OA publication ratio":"#D3D3D3"},
                                     barmode="stack",
                                     hover_data=["#OA Publications","#Non-OA Publications"])
                        if cit_ratio:
                            fig.add_scatter(x=last_20_oa["Date year"], y=last_20_oa["%Cited OA papers"],
                                            mode="lines+markers", name="%Cited OA", line=dict(color="blue"))
                            fig.add_scatter(x=last_20_oa["Date year"], y=last_20_oa["%Cited non-OA papers"],
                                            mode="lines+markers", name="%Cited non-OA", line=dict(color="red"))
                        st.plotly_chart(fig, use_container_width=True)

                    with col2:
                        last_5_oa  = st.checkbox("Limit to last 5 years", key="last5years0")
                        df_pie_oa  = df_oa_time[df_oa_time["Date year"] >= (df_oa_time["Date year"].max() - 5)] if last_5_oa else df_oa_time
                        fig = px.pie(
                            values=[df_pie_oa["#OA Publications"].sum(), df_pie_oa["#Non-OA Publications"].sum()],
                            names=["OA Publications","Non-OA Publications"],
                            title="OA vs Non-OA" + (" (last 5 years)" if last_5_oa else " (all items)"),
                            color_discrete_sequence=["green","#D3D3D3"],
                        )
                        st.plotly_chart(fig)

                oa_charts()

                st.divider()
                st.subheader("Publications by citation status", anchor=False, divider="blue")

                @st.fragment
                def cited_status_charts():
                    df_cit_sum  = df_dedup_v2.groupby("Date year")["Citation"].sum().reset_index()
                    grouped_cit = df_dedup_v2.groupby("Date year")
                    total_cit   = grouped_cit.size().reset_index(name="Total Publications")
                    cited_cit   = grouped_cit["Citation status"].apply(lambda x: (x==True).sum()).reset_index(name="Cited Publications")
                    df_cit_time = pd.merge(total_cit, cited_cit, on="Date year")
                    df_cit_time = pd.merge(df_cit_time, df_cit_sum, on="Date year")
                    df_cit_time["Non-cited Publications"]  = df_cit_time["Total Publications"] - df_cit_time["Cited Publications"]
                    df_cit_time["%Cited Publications"]     = round(df_cit_time["Cited Publications"] / df_cit_time["Total Publications"], 3) * 100
                    df_cit_time["%Non-Cited Publications"] = 100 - df_cit_time["%Cited Publications"]

                    col1, col2 = st.columns(2)
                    with col1:
                        last_20_cit = df_cit_time[df_cit_time["Date year"] >= (df_cit_time["Date year"].max() - 20)]
                        add_count   = st.checkbox("Add citation count")
                        fig = go.Figure()
                        fig.add_trace(go.Bar(x=last_20_cit["Date year"], y=last_20_cit["%Cited Publications"],
                                             name="%Cited", marker_color="#17becf"))
                        fig.add_trace(go.Bar(x=last_20_cit["Date year"], y=last_20_cit["%Non-Cited Publications"],
                                             name="%Non-Cited", marker_color="#D3D3D3"))
                        if add_count:
                            fig.add_trace(go.Scatter(x=last_20_cit["Date year"], y=last_20_cit["Citation"],
                                                     name="#Citations", mode="lines+markers",
                                                     marker=dict(color="green"), yaxis="y2"))
                        fig.update_layout(
                            title="Cited papers ratio (last 20 Years)",
                            barmode="stack",
                            yaxis2=dict(title="#Citations", overlaying="y", side="right") if add_count else {},
                        )
                        st.plotly_chart(fig, use_container_width=True)

                        last_5_cit = st.checkbox("Limit to last 5 years", key="last5years1")
                        df_pie_cit = df_cit_time[df_cit_time["Date year"] >= (df_cit_time["Date year"].max() - 5)] if last_5_cit else df_cit_time
                        fig = px.pie(
                            values=[df_pie_cit["Cited Publications"].sum(), df_pie_cit["Non-cited Publications"].sum()],
                            names=["Cited","Non-cited"],
                            title="Cited vs Non-cited" + (" (last 5 years)" if last_5_cit else " (all items)"),
                            color_discrete_sequence=["green","#D3D3D3"],
                        )
                        st.plotly_chart(fig)

                    with col2:
                        df_oa_cit  = filtered_oa.groupby("Date year")["Citation"].sum().reset_index()
                        df_oa_cit.columns = ["Date year","#Citations (OA papers)"]
                        df_all_cit = filtered_oa2.groupby("Date year")["Citation"].sum().reset_index()
                        df_all_cit.columns = ["Date year","#Citations (all)"]
                        df_cit_oa  = pd.merge(df_all_cit, df_oa_cit, on="Date year", how="left")
                        df_cit_oa["#Citations (OA papers)"].fillna(0, inplace=True)
                        df_cit_oa["#Citations (non-OA papers)"]       = df_cit_oa["#Citations (all)"] - df_cit_oa["#Citations (OA papers)"]
                        df_cit_oa["%Citation count (OA papers)"]      = round(df_cit_oa["#Citations (OA papers)"] / df_cit_oa["#Citations (all)"], 3) * 100
                        df_cit_oa["%Citation count (non-OA papers)"]  = 100 - df_cit_oa["%Citation count (OA papers)"]

                        last_20_coa = df_cit_oa[df_cit_oa["Date year"] >= (df_cit_oa["Date year"].max() - 20)]
                        line_show   = st.toggle("Citation count graph")
                        if line_show:
                            fig = go.Figure()
                            fig.add_trace(go.Scatter(x=last_20_coa["Date year"], y=last_20_coa["#Citations (OA papers)"],
                                                     mode="lines+markers", name="#Citations (OA)", line=dict(color="goldenrod")))
                            fig.add_trace(go.Scatter(x=last_20_coa["Date year"], y=last_20_coa["#Citations (non-OA papers)"],
                                                     mode="lines+markers", name="#Citations (non-OA)", line=dict(color="#D3D3D3")))
                            fig.update_layout(title="Citation Counts OA vs non-OA (last 20 Years)")
                            st.plotly_chart(fig, use_container_width=True)
                        else:
                            fig = px.bar(last_20_coa, x="Date year",
                                         y=["%Citation count (OA papers)","%Citation count (non-OA papers)"],
                                         title="OA vs non-OA Citation Count Ratio (last 20 Years)",
                                         color_discrete_map={"%Citation count (OA papers)":"goldenrod",
                                                             "%Citation count (non-OA papers)":"#D3D3D3"},
                                         barmode="stack",
                                         hover_data=["#Citations (OA papers)","#Citations (non-OA papers)"])
                            st.plotly_chart(fig, use_container_width=True)

                        last_5_coa = st.checkbox("Limit to last 5 years", key="last5years2")
                        df_pie_coa = df_cit_oa[df_cit_oa["Date year"] >= (df_cit_oa["Date year"].max() - 5)] if last_5_coa else df_cit_oa
                        fig = px.pie(
                            values=[df_pie_coa["#Citations (OA papers)"].sum(), df_pie_coa["#Citations (non-OA papers)"].sum()],
                            names=["#Citations (OA)","#Citations (non-OA)"],
                            title="OA vs non-OA citations" + (" (last 5 years)" if last_5_coa else " (all items)"),
                            color_discrete_sequence=["#D3D3D3","goldenrod"],
                        )
                        st.plotly_chart(fig)

                cited_status_charts()

                st.divider()
                st.subheader('Country mentions in titles', anchor=False, divider='blue') 


                # Load your country data with counts
                df_countries = pd.read_csv('countries.csv')
                df_countries['Country'] = df_countries['Country'].replace("UK", "United Kingdom")
                df_countries = df_countries.groupby('Country', as_index=False).sum()

                # Function to get coordinates
                def get_coordinates(country_name):
                    try:
                        country = CountryInfo(country_name)
                        return country.info().get('latlng', (None, None))
                    except KeyError:
                        return None, None

                # Apply the function to each country to get latitude and longitude
                df_countries[['Latitude', 'Longitude']] = df_countries['Country'].apply(lambda x: pd.Series(get_coordinates(x)))

                # Set a scaling factor and minimum radius to make circles larger
                scaling_factor = 500  # Adjust this to control the overall size of the circles
                minimum_radius = 100000  # Minimum radius for visibility of all points

                # Calculate the circle size based on `Count`
                df_countries['size'] = df_countries['Count'] * scaling_factor + minimum_radius

                # Filter out rows where coordinates were not found
                df_countries = df_countries.dropna(subset=['Latitude', 'Longitude'])

                # ScatterplotLayer to show countries and their mentions count
                scatterplot_layer = pdk.Layer(
                    "ScatterplotLayer",
                    data=df_countries,
                    get_position=["Longitude", "Latitude"],
                    get_radius="size",
                    get_fill_color="[255, 140, 0, 160]",  # Adjusted color with opacity
                    pickable=True,
                    auto_highlight=True,
                    id="country-mentions-layer",
                )

                # Define the view state of the map
                view_state = pdk.ViewState(
                    latitude=20, longitude=0, zoom=1, pitch=30
                )

                # Create the Deck with the layer, view state, and map style
                chart = pdk.Deck(
                    layers=[scatterplot_layer],
                    initial_view_state=view_state,
                    tooltip={"text": "{Country}\nMentions: {Count}"},
                    map_style="light",  # ← change this line
                )

                # Display the Pydeck chart in Streamlit

                col1, col2 = st.columns([8,2])
                with col1:
                    df_countries = pd.read_csv('countries.csv')
                    df_countries['Country'] = df_countries['Country'].replace("UK", "United Kingdom")
                    df_countries = df_countries.groupby('Country', as_index=False).sum()
                    df_countries = df_countries.sort_values(by='Count', ascending=False).reset_index(drop=True)
                    df_countries = df_countries.rename(columns={'Count': '# Mentions'})
                    fig = px.choropleth(df_countries, locations='Country', locationmode='country names', color='# Mentions', 
                                title='Country mentions in titles', color_continuous_scale='Viridis',
                                width=900, height=700) # Adjust the size of the map here
                    # # Display the map
                    # fig.show()
                    # st.plotly_chart(fig, use_container_width=True) 
                    st.pydeck_chart(chart, use_container_width=True)
                with col2:
                    fig = px.bar(df_countries.head(15).iloc[::-1], x='# Mentions', y='Country', orientation='h', height=600)
                    st.dataframe(df_countries, height=500, hide_index=True, use_container_width=True)
                

                st.divider()
                st.subheader("Locations, People, and Organisations", anchor=False, divider="blue")
                st.info("Named Entity Recognition (NER) retrieves locations, people, and organisations from titles and abstracts. [What is NER?](https://medium.com/mysuperai/what-is-named-entity-recognition-ner-and-how-can-i-use-it-2b68cf6f545d)")

                col1, col2, col3 = st.columns(3)
                with col1:
                    gpe = pd.read_csv("gpe.csv")
                    st.plotly_chart(px.bar(gpe.head(15), x="GPE", y="count", height=600,
                                           title="Top 15 locations").update_xaxes(tickangle=-65), use_container_width=True)
                with col2:
                    per = pd.read_csv("person.csv")
                    st.plotly_chart(px.bar(per.head(15), x="PERSON", y="count", height=600,
                                           title="Top 15 persons").update_xaxes(tickangle=-65), use_container_width=True)
                with col3:
                    org = pd.read_csv("org.csv")
                    st.plotly_chart(px.bar(org.head(15), x="ORG", y="count", height=600,
                                           title="Top 15 organisations").update_xaxes(tickangle=-65), use_container_width=True)

                st.write("---")
                st.subheader("Wordcloud", anchor=False, divider="blue")
                wordcloud_opt = st.radio("Wordcloud of:", ("Titles","Abstracts"), horizontal=True)
                df_wc     = df_csv.copy()
                df_abs_no = df_wc.dropna(subset=["Abstract"])
                if wordcloud_opt == "Abstracts":
                    st.warning(f"Not all items have an abstract. Items with an abstract: {len(df_abs_no)}.")
                    df_wc["Title"] = df_wc["Abstract"].astype(str)
                render_wordcloud(df_wc, title=f"Top words in {'abstracts' if wordcloud_opt == 'Abstracts' else 'titles'}")

            st.divider()
            st.subheader("Item inclusion history", anchor=False, divider="blue")

            @st.fragment
            def fragment_item_inclusion():
                st.write("This part shows the number of items added to the bibliography over time.")
                df_inc = df_dedup.copy()
                df_inc["Date added"] = pd.to_datetime(df_inc["Date added"])
                time_interval = st.selectbox("Select time interval:", ["Yearly","Monthly"])
                col11, col12 = st.columns(2)

                df_inc["YearMonth"] = df_inc["Date added"].dt.to_period("M").astype(str)
                monthly_inc = df_inc.groupby("YearMonth").size().rename("Number of items added")

                with col11:
                    if time_interval == "Yearly":
                        df_inc["Year"] = df_inc["Date added"].dt.to_period("Y").astype(str)
                        yearly_inc = df_inc.groupby("Year").size().rename("Number of items added")
                        bar = (alt.Chart(yearly_inc.reset_index())
                               .mark_bar()
                               .encode(x="Year", y="Number of items added", tooltip=["Year","Number of items added"])
                               .properties(width=600, title="Number of Items Added per Year"))
                        st.altair_chart(bar, use_container_width=True)
                    else:
                        bar = (alt.Chart(monthly_inc.reset_index())
                               .mark_bar()
                               .encode(x="YearMonth", y="Number of items added", tooltip=["YearMonth","Number of items added"])
                               .properties(width=600, title="Number of Items Added per Month"))
                        st.altair_chart(bar, use_container_width=True)

                with col12:
                    if time_interval == "Monthly":
                        cum = monthly_inc.cumsum()
                        line = (alt.Chart(pd.DataFrame({"YearMonth": cum.index, "Cumulative": cum}))
                                .mark_line()
                                .encode(x="YearMonth", y="Cumulative", tooltip=["YearMonth","Cumulative"])
                                .properties(width=600, title="Cumulative Number of Items Added"))
                        st.altair_chart(line, use_container_width=True)
                    else:
                        yearly_inc = df_inc.groupby("Year").size().rename("Number of items added")
                        cum_y = yearly_inc.cumsum()
                        line = (alt.Chart(pd.DataFrame({"Year": cum_y.index, "Cumulative": cum_y}))
                                .mark_line()
                                .encode(x="Year", y="Cumulative", tooltip=["Year","Cumulative"])
                                .properties(width=600, title="Cumulative Number of Items Added"))
                        st.altair_chart(line, use_container_width=True)

            fragment_item_inclusion()
        else:
            st.info("Toggle to see the dashboard!")

st.write("---")
with st.expander("Acknowledgements"):
    st.subheader("Acknowledgements", anchor=False)
    st.write("""
    The following sources are used to collate some of the items and events in this website:
    1. [King's Centre for the Study of Intelligence (KCSI) digest](https://kcsi.uk/kcsi-digests) compiled by Kayla Berg
    2. [International Association for Intelligence Education (IAIE) digest](https://www.iafie.org/Login.aspx) compiled by Filip Kovacevic

    Contributors with comments and sources:
    1. Daniela Richterove
    2. Steven Wagner
    3. Sophie Duroy

    Proudly sponsored by the [King's Centre for the Study of Intelligence](https://kcsi.uk/)
    """)

display_custom_license()