import os
import time
from concurrent.futures import ThreadPoolExecutor

import requests
import streamlit as st

API_URL = "https://api.fireworks.ai/inference/v1/chat/completions"
CUSTOM = "Custom model ID…"
MODELS_URL = "https://api.fireworks.ai/inference/v1/models"
FALLBACK_MODELS = [
    "accounts/fireworks/models/gpt-oss-120b",
    "accounts/fireworks/models/gpt-oss-20b",
    "accounts/fireworks/models/deepseek-v3p1",
    "accounts/fireworks/models/kimi-k2-instruct-0905",
    "accounts/fireworks/models/qwen3-235b-a22b-instruct-2507",
    "accounts/fireworks/models/llama-v3p3-70b-instruct",
]


@st.cache_data(ttl=3600, show_spinner=False)
def list_models(api_key):
    """Serverless models available to this key; falls back to a curated list."""
    if not api_key:
        return FALLBACK_MODELS
    try:
        resp = requests.get(MODELS_URL, headers={"Authorization": f"Bearer {api_key}"}, timeout=15)
        resp.raise_for_status()
        ids = sorted(m["id"] for m in resp.json().get("data", []) if m.get("id"))
        return ids or FALLBACK_MODELS
    except Exception:
        return FALLBACK_MODELS


def get_default_key():
    try:
        return st.secrets.get("FIREWORKS_API_KEY", "")
    except Exception:
        return os.environ.get("FIREWORKS_API_KEY", "")


def call_model(api_key, model, prompt, max_tokens, temperature):
    start = time.perf_counter()
    try:
        resp = requests.post(
            API_URL,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": max_tokens,
                "temperature": temperature,
            },
            timeout=120,
        )
        elapsed = time.perf_counter() - start
        if not resp.ok:
            return {"error": f"HTTP {resp.status_code}: {resp.text[:500]}", "seconds": elapsed}
        data = resp.json()
        return {
            "text": data["choices"][0]["message"]["content"],
            "seconds": elapsed,
            "tokens": data.get("usage", {}).get("completion_tokens"),
        }
    except Exception as e:
        return {"error": str(e), "seconds": time.perf_counter() - start}


def model_picker(label, models, default, key):
    options = models + [CUSTOM]
    index = options.index(default) if default in options else 0
    choice = st.selectbox(label, options, index=index, key=key,
                          format_func=lambda m: m.rsplit("/", 1)[-1] if m != CUSTOM else m)
    if choice == CUSTOM:
        choice = st.text_input("Model ID", placeholder="accounts/fireworks/models/...", key=f"{key}_custom").strip()
    return choice


def show_result(model, result):
    st.subheader(model.rsplit("/", 1)[-1] if model else "—")
    if "error" in result:
        st.error(result["error"])
        st.caption(f"Failed after {result['seconds']:.2f}s")
        return
    caption = f"⏱ {result['seconds']:.2f}s"
    if result.get("tokens"):
        caption += f" · {result['tokens']} tokens · {result['tokens'] / result['seconds']:.1f} tok/s"
    st.metric("Response time", f"{result['seconds']:.2f}s")
    st.caption(caption)
    st.markdown(result["text"])


st.set_page_config(page_title="ModelForge", page_icon="⚒️", layout="wide")
st.title("⚒️ ModelForge")
st.caption("Compare two Fireworks AI models side by side.")

with st.sidebar:
    st.header("Settings")
    api_key = st.text_input("Fireworks API key", value=get_default_key(), type="password")
    max_tokens = st.slider("Max tokens", 64, 4096, 512, step=64)
    temperature = st.slider("Temperature", 0.0, 2.0, 0.7, step=0.1)

models = list_models(api_key)
col_a, col_b = st.columns(2)
with col_a:
    model_a = model_picker("Model A", models, FALLBACK_MODELS[0], "model_a")
with col_b:
    model_b = model_picker("Model B", models, FALLBACK_MODELS[2], "model_b")

prompt = st.text_area("Prompt", height=150, placeholder="Ask both models the same thing…")

if st.button("Compare", type="primary", use_container_width=True):
    if not api_key:
        st.warning("Add your Fireworks API key in the sidebar.")
    elif not prompt.strip():
        st.warning("Enter a prompt.")
    elif not model_a or not model_b:
        st.warning("Choose both models.")
    else:
        with st.spinner("Running both models…"):
            with ThreadPoolExecutor(max_workers=2) as pool:
                fa = pool.submit(call_model, api_key, model_a, prompt, max_tokens, temperature)
                fb = pool.submit(call_model, api_key, model_b, prompt, max_tokens, temperature)
                st.session_state.results = (model_a, fa.result(), model_b, fb.result())

if "results" in st.session_state:
    ma, ra, mb, rb = st.session_state.results
    out_a, out_b = st.columns(2)
    with out_a:
        show_result(ma, ra)
    with out_b:
        show_result(mb, rb)
