# Streamlit frontend

Run these commands from the repository root in your project Python environment:

```powershell
python -m pip install -r src/frontend/requirements.txt
python -m streamlit run src/frontend/app.py
```

The three screens are the starting page (`?page=home`), login (`?page=login`),
and signup (`?page=signup`). Components, views, and styling are contained in this
folder. The layout adapts to narrow screens.

Login and logout use the existing API at `http://127.0.0.1:8000/api/v1`.
Start the backend separately. Set `NASA_API_URL` in the server environment to
change the API base URL; the frontend does not load the root `.env` file.

The signup page follows the supplied identification/full-name/password design.
It validates fields but cannot create an account yet: the backend registration
contract instead requires username, email, password, and birth date. Password
recovery is also pending a backend endpoint. Neither action displays fake success.
Remember me on login retains only the username for the current Streamlit session;
it does not provide persistent authentication. The signup checkbox is visual only.

Run the frontend checks with:

```powershell
python -m unittest discover -s tests -p test_frontend.py
```
