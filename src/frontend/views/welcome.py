"""Welcome / About Us screen and the application's collapsible navigation."""

import streamlit as st

from frontend import api
from frontend.components.layout import navigate
from frontend.components.session import clear_session, require_session, show_api_error
from frontend.views import information, measurements
from frontend.views.temperature import render_temperature
from frontend.views.microcirculation import render_microcirculation
from frontend.views.reliability import render_reliability
from frontend.views.statistical_analysis import render_statistical_analysis


SECTIONS = {
    "mission": "Our Mission",
    "features": "Features",
    "temperature": "Temperature",
    "microcirculation": "Microcirculation",
    "reliability": "Measurement Reliability",
    "analysis": "Statistical Analysis",
    "profile": "My Profile",
    "collect": "Record a Measurement",
    "history": "Measurement History",
    "daily": "Daily Summaries",
    "analytics": "Period Analytics",
}


def toggle_navigation() -> None:
    st.session_state["drawer_is_open"] = not st.session_state.get("drawer_is_open", True)


def select_section(section: str) -> None:
    st.query_params["page"] = "welcome"
    st.query_params["section"] = section
    st.session_state["drawer_is_open"] = False


def sign_out() -> None:
    try:
        api.logout(st.session_state["access_token"])
    except api.ApiError as error:
        st.session_state["logout_notice"] = str(error)
    finally:
        clear_session()
    navigate("login")


def render() -> None:
    section = st.query_params.get("section", "welcome")
    if section not in SECTIONS and section != "welcome":
        section = "welcome"
    opened = st.session_state.setdefault("drawer_is_open", section == "welcome")

    with st.container(key="workspace"):
        if opened:
            with st.container(key="app_navigation"):
                st.button("Close navigation", key="navigation_close", on_click=toggle_navigation)
                with st.container(key="navigation_links"):
                    for slug, label in SECTIONS.items():
                        st.button(label, key=f"section_{slug}", on_click=select_section, args=(slug,))
                if st.session_state.get("access_token"):
                    st.button("Log Out", key="navigation_logout", on_click=sign_out)
        else:
            st.button("Open navigation", key="navigation_open", on_click=toggle_navigation)

        if section in {"mission", "features"}:
            information.render(section)
            return

        with st.container(key="workspace_content_open" if opened else "workspace_content_closed"):
            if section == "welcome":
                st.markdown('<h1 class="workspace-title">WELCOME</h1>', unsafe_allow_html=True)
                st.markdown(
                    '<section class="about-copy" aria-labelledby="about-title">'
                    '<h2 id="about-title">ABOUT US</h2>'
                    '<p>Space exploration has taught us to push the boundaries of technology. '
                    'Now, it is time to understand the limits of our own bodies.</p>'
                    '<p>We are Space Dracula, a team that brings together science, technology, '
                    'and creativity to tackle the challenges of living beyond Earth.</p>'
                    '<p>We believe that the future of space exploration is not just about building '
                    'spacecraft capable of travelling further, but also about developing tools that '
                    'help humans adapt to environments our bodies were never designed for.</p>'
                    '</section>',
                    unsafe_allow_html=True,
                )
            else:
                token = require_session()
                try:
                    with st.spinner('Checking your session…'):
                        user = api.request('GET', '/auth/me', token)
                    st.session_state['user'] = user
                    renderers = {
                        'temperature': render_temperature,
                        'microcirculation': render_microcirculation,
                        'reliability': render_reliability,
                        'analysis': render_statistical_analysis,
                        'profile': lambda: measurements.render_profile(user),
                        'collect': lambda: measurements.render_collection(token),
                        'history': lambda: measurements.render_history(token),
                        'daily': lambda: measurements.render_daily(token),
                        'analytics': lambda: measurements.render_analytics(token),
                    }
                    renderers[section]()
                except api.ApiError as error:
                    show_api_error(error)
                    st.button('Retry connection')
