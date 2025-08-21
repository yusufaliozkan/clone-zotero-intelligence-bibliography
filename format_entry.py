def format_entry(row, include_citation=False, reviews_map=None):
    # --- existing fields you already compute ---
    citation       = row.get("citation_count", 0)  # adjust to your actual field
    citation_link  = row.get("citation_link", "")
    link_to_publication = row.get("Link to publication") or ""
    zotero_link    = row.get("Zotero link") or ""
    oa_url         = str(row.get("OA_link") or "")
    oa_url_fixed   = oa_url.replace(" ", "%20")

    pub_link_badge    = f"[:blue-badge[Publication link]]({link_to_publication})" if link_to_publication else ""
    zotero_link_badge = f"[:blue-badge[Zotero link]]({zotero_link})" if zotero_link else ""
    oa_link_text      = f"[:green-badge[OA version]]({oa_url_fixed})" if oa_url_fixed else ""
    citation_text     = f"[:orange-badge[Cited by {citation}]]({citation_link})" if citation and citation_link else ""

    # --- NEW: book reviews badge (uses injected reviews_map) ---
    # Find parentKey either from the row, or parse it from the Zotero URL
    parent_key = row.get("parentKey")
    if not parent_key and pd.notna(row.get("Zotero link")):
        parent_key = row["Zotero link"].rstrip("/").split("/")[-1]

    links = reviews_full_map.get(parent_key, [])

    # show a popover listing ALL reviews
    if links:
        with st.popover(f"All reviews ({len(links)})", use_container_width=True):
            for j, r in enumerate(links, 1):
                st.markdown(f"{j}. [{r['title_']}]({r['url']})")

    # --- Your existing formatting branches ---
    publication_type = row.get("Publication type", "")
    title            = row.get("Title", "")
    authors          = row.get("FirstName2", "")
    date_published   = row.get("Date published", "")
    book_title       = row.get("Book_title", "")
    thesis_type      = row.get("Thesis_type", "")
    thesis_type2     = f"{thesis_type}: " if thesis_type else ""
    university       = row.get("University", "")
    published_source = row.get("Journal") or row.get("Publisher") or ""
    published_by_or_in = "Published in" if row.get("Journal") else ("Published by" if row.get("Publisher") else "")

    badges = " ".join(filter(None, [
        pub_link_badge,
        zotero_link_badge,
        book_reviews_badge,   # <-- added here
        oa_link_text,
        citation_text if include_citation else ""
    ]))

    if publication_type == "Book chapter":
        return (
            f"**{publication_type}**: {title} "
            f"(in: *{book_title}*) "
            f"(by *{authors}*) "
            f"(Publication date: {date_published}) "
            f"{badges}"
        )
    elif publication_type == "Thesis":
        return (
            f"**{publication_type}**: {title} "
            f"({thesis_type2}*{university}*) "
            f"(by *{authors}*) "
            f"(Publication date: {date_published}) "
            f"{badges}"
        )
    else:
        return (
            f"**{publication_type}**: {title} "
            f"(by *{authors}*) "
            f"(Publication date: {date_published}) "
            f"{f'({published_by_or_in}: *{published_source}*) ' if published_by_or_in else ''}"
            f"{badges}"
        )
