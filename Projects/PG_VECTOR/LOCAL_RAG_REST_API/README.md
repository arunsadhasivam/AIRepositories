# Local RAG with Python and Flask

This application is designed to handle queries using a language model and a vector database. It generates multiple versions of a user query to retrieve relevant documents and provides answers based on the retrieved context.

## Prerequisites

1. **Python 3**: Ensure you have Python 3.x installed.
2. **Ollama**: This app requires Ollama to be installed and running locally. Follow the [Ollama installation guide](https://github.com/ollama/ollama/blob/main/README.md#quickstart) to set it up.


## Setup

1. **Clone the repository**:
```bash
$ git clone https://github.com/your-repo/LOCAL_RAG_REST_API.git
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

## Conclusion

This app leverages a language model and a vector database to provide enhanced query handling capabilities. Ensure Ollama is running locally and follow the setup instructions to get started.


## chroma db

all uploaded embedding will be stored in the .env path

    TEMP_FOLDER = 'C:\Arun\RAG_DATA\TEMP'
    CHROMA_PATH = "C:\Arun\RAG_DATA\VECTOR_DB\CHROMA"


![image](https://github.com/user-attachments/assets/75dbd39a-888b-4999-a40c-6445080b7830)
![image](https://github.com/user-attachments/assets/94ea6ef3-4f9f-46e1-bc2d-cb96779ded15)


## Agent ##

## if response is is "is_math_required" is true local python math function no processing time

![image](https://github.com/user-attachments/assets/2aef6f56-6ca4-46c4-8d75-242005fed50a)


## ollama prediction from RAG

![image](https://github.com/user-attachments/assets/5791ad81-9b29-4a31-9646-0e86e1807af5)
![image](https://github.com/user-attachments/assets/b4f68192-ecc2-4693-b16a-051005afa71e)
