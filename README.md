# ModelForge

A minimal Streamlit app that compares two [Fireworks AI](https://fireworks.ai) models side by side.

- Two model selectors (models available to your key, loaded from the Fireworks API, or any custom model ID)
- One shared prompt
- A **Compare** button that queries both models in parallel
- Response time (and tokens/sec) for each model

No backend server, database, or frontend framework — just one Python file.

## Run

```bash
pip install -r requirements.txt
streamlit run app.py
```

Enter your Fireworks API key in the sidebar, or provide it ahead of time with either:

- `export FIREWORKS_API_KEY=fw_...`
- `.streamlit/secrets.toml` containing `FIREWORKS_API_KEY = "fw_..."` (git-ignored)
