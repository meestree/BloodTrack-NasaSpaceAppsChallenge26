"""Run with: streamlit run src/frontend/app.py."""

from pathlib import Path
import sys

import streamlit as st

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from frontend.components.layout import LOGO_PATH, load_styles
from frontend import api
from frontend.views import about, home, loading, signup, welcome


def main() -> None:
    st.set_page_config(page_title="BloodTrack", page_icon=str(LOGO_PATH), layout="centered", initial_sidebar_state="collapsed")
    api.begin_run()
    load_styles()
    views = {"home": home.render, "login": home.render, "signup": signup.render,
             "welcome": welcome.render, "about": about.render, "loading": loading.render}
    views.get(st.query_params.get("page", "home"), home.render)()


if __name__ == "__main__":
    main()
