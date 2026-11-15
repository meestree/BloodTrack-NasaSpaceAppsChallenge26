"""Mission and features copy transcribed from the supplied Figma screenshots."""

from html import escape

import streamlit as st


MISSION = (
    "In space, even blood changes its course.",
    "On Earth, gravity influences how blood is distributed throughout our bodies. In space, "
    "microgravity disrupts this balance, causing changes in circulation and bodily functions "
    "that can put astronauts' health at risk, especially during long-duration missions.",
    "How can we protect astronauts if we don't understand how their bodies are responding?",
    "At Space Dracula, we want to make these changes visible. Our application monitors "
    "temperature and microcirculation indicators in different parts of the body, detects "
    "deviations from normal reference values, and tracks how these parameters evolve over time.",
    "By doing so, we aim to help identify potential abnormalities and provide valuable "
    "information to support astronauts' health monitoring.",
    "Because exploring space shouldn't mean losing sight of what's happening inside our bodies.",
)

FEATURES = (
    ("01. Temperature", "Track skin temperature in different body regions using a color-coded map to highlight deviations from normal ranges."),
    ("02. Microcirculation", "Visualize blood flow indicators across the body and identify potential circulatory changes."),
    ("03. Reliability", "Monitor astronaut movement to detect when sensor measurements may be unreliable."),
    ("04. Statistical Analysis", "Explore temperature and microcirculation trends through graphs with statistical averages, standard deviations, and reference limits."),
    ("05. Daily Summaries", "Review daily sample counts, average temperature and microcirculation, and movement-marked sample counts by body region and UTC date. Filter by time window and body region to compare recorded days."),
)


def render_about() -> None:
    """Combined team vision and features, shared by the index and About Us page."""
    with st.container(key="about_us"):
        mission = ''.join(f'<p>{escape(paragraph)}</p>' for paragraph in MISSION)
        features = ''.join(f'<h3>{escape(label)}</h3><p>{escape(description)}</p>'
                           for label, description in FEATURES)
        st.html(
            '<section class="about-us-copy" aria-labelledby="about-us-title">'
            '<h2 id="about-us-title">About Us</h2>'
            '<p>We are Space Dracula, a team bringing together science, technology, '
            'and creativity to tackle the challenges of living beyond Earth.</p>'
            f'<h3>Our mission</h3>{mission}'
            f'<h3>Features</h3>{features}</section>'
        )


def render(section: str) -> None:
    title = "OUR MISSION" if section == "mission" else "FEATURES"
    with st.container(key="editorial"):
        st.markdown(f'<h1 class="editorial-title">{title}</h1>', unsafe_allow_html=True)
        if section == "mission":
            content = "".join(f"<p>{escape(paragraph)}</p>" for paragraph in MISSION)
        else:
            content = (
                '<p>Discover how Space Dracula transforms physiological data into clear, visual insights '
                "to better understand the human body's response to microgravity.</p>"
            )
            for label, description in FEATURES:
                content += f'<h2>{escape(label)}</h2><p>{escape(description)}</p>'
        st.markdown(f'<article class="editorial-copy {section}-copy">{content}</article>', unsafe_allow_html=True)
