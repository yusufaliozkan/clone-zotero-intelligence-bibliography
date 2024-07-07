def get_copyright_annotation():
    cc_by_image_url  = "https://i.creativecommons.org/l/by/4.0/80x15.png"
    return [
        dict(
            x=0.1,
            y=-0.2,
            xref='paper',
            yref='paper',
            showarrow=False,
            text=(
                "© 2024 Yusuf Ozkan. All rights reserved. "
                '<img src="' + cc_by_image_url + '" style="height:20px; vertical-align:middle;">'
            ),
            xanchor='center',
            yanchor='top',
            font=dict(
                size=12
            )
        )
    ]