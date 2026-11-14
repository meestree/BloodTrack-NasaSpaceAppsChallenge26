"""Exercise the three screens and authentication transitions without a live API."""

from pathlib import Path
import sys
import unittest
from unittest.mock import patch

try:
    from streamlit.testing.v1 import AppTest
except ModuleNotFoundError as error:
    if error.name != "streamlit":
        raise
    AppTest = None

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from frontend import api


@unittest.skipIf(AppTest is None, "Install src/frontend/requirements.txt to test the frontend")
class FrontendTests(unittest.TestCase):
    def app(self, page="home"):
        app = AppTest.from_file(str(ROOT / "src" / "frontend" / "app.py"))
        app.query_params["page"] = page
        app.run()
        self.assertFalse(app.exception)
        return app

    def test_start_page_links_to_both_forms(self):
        for label, page in (("Log In", "login"), ("Get started", "signup")):
            with self.subTest(page=page):
                app = self.app()
                next(button for button in app.button if button.label == label).click().run()
                self.assertEqual(app.query_params["page"], page)
                self.assertFalse(app.exception)

    def test_login_requires_credentials(self):
        app = self.app("login")
        with patch.object(api, "login") as login:
            app.button[0].click().run()
        login.assert_not_called()
        self.assertEqual(app.error[0].value, "Enter your user and password.")

    def test_login_success_and_logout(self):
        app = self.app("login")
        app.text_input[0].set_value("astronaut")
        app.text_input[1].set_value("example-password")
        with patch.object(api, "login", return_value=("test-token", {"nombre_usuario": "astronaut"})):
            app.button[0].click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state["access_token"], "test-token")
        self.assertEqual(app.query_params["page"], "welcome")
        with patch.object(api, "logout") as logout:
            app.button(key="navigation_logout").click().run()
        logout.assert_called_once_with("test-token")
        self.assertNotIn("access_token", app.session_state)
        self.assertEqual(app.title[0].value, "Log In")

    def test_login_service_failure_is_visible(self):
        app = self.app("login")
        app.text_input[0].set_value("astronaut")
        app.text_input[1].set_value("example-password")
        with patch.object(api, "login", side_effect=api.ApiError("Cannot reach the service.")):
            app.button[0].click().run()
        self.assertEqual(app.error[0].value, "Cannot reach the service.")
        self.assertNotIn("access_token", app.session_state)

    def test_signup_uses_design_fields_and_validates(self):
        app = self.app("signup")
        self.assertEqual([field.label for field in app.text_input], ["Number of Identification", "Full Name", "Password"])
        app.button[0].click().run()
        self.assertEqual(app.error[0].value, "Complete all three fields.")
        app.text_input[0].set_value("123456")
        app.text_input[1].set_value("Example Person")
        app.text_input[2].set_value("example-password")
        app.button[0].click().run()
        self.assertFalse(app.exception)
        self.assertTrue(app.info)
        self.assertFalse(app.success)  # The API does not support these registration fields yet.

    def test_welcome_navigation_can_close_reopen_and_select_sections(self):
        app = self.app("welcome")
        self.assertIn("Space Dracula", " ".join(item.value for item in app.markdown))
        app.button(key="navigation_close").click().run()
        self.assertFalse(app.session_state["drawer_is_open"])
        self.assertFalse(any(button.key == "section_mission" for button in app.button))
        app.button(key="navigation_open").click().run()
        self.assertTrue(app.session_state["drawer_is_open"])
        for section in ("features", "temperature", "microcirculation", "reliability", "analysis", "mission"):
            if not app.session_state["drawer_is_open"]:
                app.button(key="navigation_open").click().run()
            app.button(key=f"section_{section}").click().run()
            self.assertEqual(app.query_params["section"], section)
            self.assertFalse(app.exception)
            self.assertFalse(app.session_state["drawer_is_open"])
            if section == "mission":
                content = " ".join(item.value for item in app.markdown)
                self.assertIn("OUR MISSION", content)
                self.assertIn("In space, even blood changes its course.", content)
            elif section == "features":
                content = " ".join(item.value for item in app.markdown)
                self.assertIn("FEATURES", content)
                self.assertIn("04. Data Analysis", content)


if __name__ == "__main__":
    unittest.main()
