def format_entry(row, include_citation=False, reviews_map=None):
    # accept Series or dict
    if hasattr(row, "to_dict"):
        row = row.to_dict()

    import pandas as pd

    def _clean(x):
        return str(x).strip() if (x is not None and not (isinstance(x, float) and pd.isna(x)) and not (hasattr(pd, "isna") and pd.isna(x))) and str(x).strip() else ""

    # --- fields ---
    citation            = row.get("Citation", 0) or row.get("citation_count", 0)
    citation_link       = _clean(row.get("citation_link"))
    link_to_publication = _clean(row.get("Link to publication"))
    zotero_link         = _clean(row.get("Zotero link"))
    oa_url_fixed        = _clean(row.get("OA_link")).replace(" ", "%20")

    pub_link_badge     = f"[:blue-badge[Publication link]]({link_to_publication})" if link_to_publication else ""
    zotero_link_badge  = f"[:blue-badge[Zotero link]]({zotero_link})" if zotero_link else ""
    oa_link_text       = f"[:green-badge[OA version]]({oa_url_fixed})" if oa_url_fixed else ""
    citation_text      = f"[:orange-badge[Cited by {citation}]]({citation_link})" if citation and citation_link else ""

    # --- book reviews badge ---
    parent_key = row.get("parentKey")
    if not parent_key and zotero_link:
        parent_key = zotero_link.rstrip("/").split("/")[-1]

    # --- NEW: multiple inline review badges ---
    book_review_badges = ""
    if reviews_map:
        links = reviews_map.get(parent_key) or []
        if links:
            n = len(links) if max_reviews_inline is None else min(len(links), max_reviews_inline)
            book_review_badges = " ".join(
                f"[:violet-badge[Book review {i+1}]]({links[i]})" for i in range(n)
            )
            # Optional: if you cap, show a "+N more" linking to the latest (or a popover elsewhere)
            if max_reviews_inline is not None and len(links) > n:
                book_review_badges += f" [:violet-badge[+{len(links)-n} more]]({links[0]})"

    # Build the common badges string
    badges = " ".join(filter(None, [
        pub_link_badge,
        zotero_link_badge,
        book_review_badges,   # <-- use the multi-badge string here
        oa_link_text,
        citation_text if include_citation else ""
    ]))

    # --- display fields ---
    publication_type   = _clean(row.get("Publication type"))
    title              = _clean(row.get("Title"))
    authors            = _clean(row.get("FirstName2"))
    date_published     = _clean(row.get("Date published"))
    book_title         = _clean(row.get("Book_title"))
    thesis_type        = _clean(row.get("Thesis_type"))
    thesis_type2       = f"{thesis_type}: " if thesis_type else ""
    university         = _clean(row.get("University"))

    # ✅ NaN-safe journal/publisher logic
    j = _clean(row.get("Journal"))
    p = _clean(row.get("Publisher"))
    if j:
        published_by_or_in, published_source = "Published in", j
    elif p:
        published_by_or_in, published_source = "Published by", p
    else:
        published_by_or_in, published_source = "", ""

    pub_src_segment = f"({published_by_or_in}: *{published_source}*) " if published_source else ""

    badges = " ".join(filter(None, [
        pub_link_badge,
        zotero_link_badge,
        book_reviews_badge,
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
        # Books (and everything else) come here
        return (
            f"**{publication_type}**: {title} "
            f"(by *{authors}*) "
            f"(Publication date: {date_published}) "
            f"{pub_src_segment}"
            f"{badges}"
        )
