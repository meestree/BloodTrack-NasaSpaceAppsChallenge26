"""Shared styles and navigation for the supplied Figma screenshots."""

from pathlib import Path
from base64 import b64encode
from functools import lru_cache

import streamlit as st
from frontend.components.assets import image_data_url


LOGO_PATH = Path(__file__).resolve().parents[1] / "assets" / "logo.png"


def render_logo() -> None:
    st.html(
        f'<div class="app-logo"><img src="{image_data_url(LOGO_PATH)}" '
        'alt="BloodTrack logo" width="112" height="112"></div>'
    )


def load_styles() -> None:
    assets = Path(__file__).resolve().parents[1] / "assets"
    paths = [assets / 'styles.css', *(assets / 'fonts').glob('*.ttf'),
             Path(__file__).resolve().parents[2] / 'resources' / 'background.png']
    versions = tuple((str(path), path.stat().st_mtime_ns) for path in paths)
    st.markdown(_style_markup(versions), unsafe_allow_html=True)


@lru_cache(maxsize=4)
def _style_markup(versions: tuple) -> str:
    assets = Path(__file__).resolve().parents[1] / "assets"
    css = (assets / "styles.css").read_text(encoding="utf-8")
    background_path = Path(__file__).resolve().parents[2] / "resources" / "background.png"
    background_css = (
        '.stApp {background-image: url("' + image_data_url(background_path) + '");'
        'background-size: cover; background-position: center; background-repeat: no-repeat;'
        'background-attachment: fixed;}'
    )
    # Embed local fonts so rendering does not depend on visitors reaching Google Fonts.
    fonts = []
    for family in ("Audiowide", "Montserrat"):
        encoded = b64encode((assets / "fonts" / f"{family}-Regular.ttf").read_bytes()).decode("ascii")
        fonts.append(
            f'@font-face {{font-family: "{family}"; font-style: normal; font-weight: 400; '
            f'font-display: swap; src: url(data:font/ttf;base64,{encoded}) format("truetype");}}'
        )
    return f"<style>{''.join(fonts)}{css}{background_css}</style>"


def navigate(page: str) -> None:
    st.query_params.pop("help", None)
    st.query_params.pop("section", None)
    st.query_params["page"] = page


def back_home() -> None:
    st.button("← Home", key="back_home", on_click=navigate, args=("home",), type="tertiary")
