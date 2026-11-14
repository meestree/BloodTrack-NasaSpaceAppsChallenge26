"""Shared styles and navigation for the supplied Figma screenshots."""

from pathlib import Path
from base64 import b64encode

import streamlit as st


def load_styles() -> None:
    assets = Path(__file__).resolve().parents[1] / "assets"
    css = (assets / "styles.css").read_text(encoding="utf-8")
    # Embed local fonts so rendering does not depend on visitors reaching Google Fonts.
    fonts = []
    for family in ("Audiowide", "Montserrat"):
        encoded = b64encode((assets / "fonts" / f"{family}-Regular.ttf").read_bytes()).decode("ascii")
        fonts.append(
            f'@font-face {{font-family: "{family}"; font-style: normal; font-weight: 400; '
            f'font-display: swap; src: url(data:font/ttf;base64,{encoded}) format("truetype");}}'
        )
    st.markdown(f"<style>{''.join(fonts)}{css}</style>", unsafe_allow_html=True)


def navigate(page: str) -> None:
    st.query_params.pop("help", None)
    st.query_params.pop("section", None)
    st.query_params["page"] = page


def back_home() -> None:
    st.button("← Home", key="back_home", on_click=navigate, args=("home",), type="tertiary")
