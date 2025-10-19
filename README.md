[![Review Assignment Due Date](https://classroom.github.com/assets/deadline-readme-button-22041afd0340ce965d47ae6ef1cefeee28c7c493a6346c4f15d667ab976d596c.svg)](https://classroom.github.com/a/PXSOX9b7)


## Repo structure

ds-25-movie-recommendation/
├── frontend/ # Streamlit web application
│ ├── init.py
│ └── main.py # Main Streamlit app entry point
├── server/ # Backend services and API logic
│ └── init.py
├── scripts/ # Utility scripts
│ └── run_local.sh # Local development runner
├── docker-compose.yml # Docker services configuration
├── Dockerfile # Container build instructions
├── pyproject.toml # Poetry dependencies and project config
├── poetry.lock # Locked dependency versions
└── README.md # Project documentation


## Setup
All code is specific for MacOS. For other OSs such as linux, please adjust accordingly.

### Poetry environment

The following requires having [poetry](https://python-poetry.org/docs/) installed.

Install python 3.12:
```
brew update
brew install pyenv
pyenv install 3.12
```

Now you can install the poetry environment for this project as follows:
```
poetry install
```

### Pre-commit hooks

Install the pre-commit hooks with:
```
poetry run pre-commit install
```
Now the [ruff](https://github.com/astral-sh/ruff) linter and formatter will run automatically before each commit.
