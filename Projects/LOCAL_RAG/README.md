# Local RAG with Python and Flask

This application is designed to handle queries using a language model and a vector database. It generates multiple versions of a user query to retrieve relevant documents and provides answers based on the retrieved context.

## Prerequisites

1. **Python 3**: Ensure you have Python 3.x installed.
2. **Ollama**: This app requires Ollama to be installed and running locally. Follow the [Ollama installation guide](https://github.com/ollama/ollama/blob/main/README.md#quickstart) to set it up.

## Setup

1. **Clone the repository**:
```bash
$ git clone https://github.com/arunsadhasivam/AIRepositories/blob/master/Projects/LOCAL_RAG.git
$ cd local-rag
```

2. **Create a virtual environment**:
```bash
$ python -m venv venv
$ source venv/bin/activate

# For Windows user
# venv\Scripts\activate
```

3. **Install dependencies**:
```bash
$ pip install -r requirements.txt
```

4. **Run Ollama**:
Ensure Ollama is installed and running locally. Refer to the [Ollama documentation](https://github.com/ollama/ollama/blob/main/README.md#quickstart) for setup instructions.
- Install llm model
```bash
$ ollama pull mistral
```
- Install text embedding model
```bash
$ ollama pull nomic-embed-text
```
- Run Ollama
```bash
$ ollama serve
```

## Running the App
```bash
$ python app.py
```

