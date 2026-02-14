# SOFTWAREFACTORY

Quickstart

1. Create a Python virtualenv and activate it:

```bash
python -m venv .venv
source .venv/bin/activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Copy the example env and fill in keys:

```bash
cp .env.example .env
# set API keys in .env
```

4. Run the dev graph (after you've installed LangGraph CLI or using the project's CLI when ready):

```bash
# example (install langgraph CLI separately)
langgraph dev
```

See `docs/PLAN.md` for the project plan and issue list.
