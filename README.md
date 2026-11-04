# 🇵🇰 PakKnowledge AI — Your Trusted Guide to Pakistan

**PakKnowledge AI** is a Pakistan-focused Retrieval-Augmented Generation (RAG) chatbot designed to provide evidence-based answers about Pakistan using a collection of indexed documents.

The application retrieves relevant information from a local knowledge base, verifies whether the retrieved evidence is sufficient, and generates answers with source citations. It is designed to avoid unsupported answers and politely decline questions outside its Pakistan-focused scope.

## ✨ Features

- **Pakistan-focused knowledge:** Answers questions about Pakistan's history, geography, government and laws, economy, education, culture, tourism, and public services.
- **Document ingestion:** Supports PDF, DOCX, and TXT files.
- **Semantic search:** Uses ChromaDB to retrieve relevant document passages.
- **RAG architecture:** Generates answers using retrieved document evidence rather than relying only on the language model's general knowledge.
- **Evidence verification:** Checks whether the retrieved passages sufficiently support an answer.
- **Source citations:** Provides references to supporting documents and available page information.
- **Scope classification:** Identifies and politely declines questions unrelated to Pakistan.
- **Abstention handling:** Avoids generating answers when the available evidence is insufficient.
- **Interactive interface:** Provides a Streamlit-based chatbot interface with theme options and chat functionality.


## Application Preview

### Desktop Interface

![PakKnowledge AI Desktop Interface](images/desktop-preview.png)

### Mobile Interface

<div align="center">

<table>
  <tr>
    <td align="center">
      <img src="images/mobile-preview-1.png" width="300" alt="Mobile View 1" />
      <br />
      <sub><b>Main Screen</b></sub>
    </td>
    <td align="center">
      <img src="images/mobile-preview-2.png" width="300" alt="Mobile View 2" />
      <br />
      <sub><b>Chat View</b></sub>
    </td>
  </tr>
</table>

</div>


## 🛠️ Technologies Used

| Technology | Purpose |
|---|---|
| Python | Core application development |
| Streamlit | Interactive web interface |
| LangGraph | Workflow orchestration |
| ChromaDB | Vector database and document retrieval |
| Groq API | Large language model inference |
| OpenAI Python SDK | API client configured for Groq |
| Sentence Transformers | Semantic embedding support |
| PyPDF | PDF document processing |
| python-docx / docx2txt | Word document processing |
| Beautiful Soup | HTML parsing support in the project |

## 🏗️ System Architecture

PakKnowledge AI follows a Retrieval-Augmented Generation workflow.

```mermaid

flowchart TD
    A["User Question"] --> B["Question Classification"]
    B --> C{"Pakistan Related?"}

    C -->|No| D["Out-of-Scope Response"]
    C -->|Yes| E["Retrieve Relevant Passages"]

    E --> F{"Sufficient Evidence?"}

    F -->|No| G["Abstain: Insufficient Evidence"]
    F -->|Yes| H["Generate Grounded Answer"]

    H --> I["Attach Source Citations"]

    D --> J["Display Response"]
    G --> J
    I --> J

```

### How It Works

1. The user submits a question through the Streamlit interface.
2. LangGraph coordinates the question-processing workflow.
3. The question is classified to determine whether it relates to Pakistan.
4. Relevant passages are retrieved from the ChromaDB knowledge base.
5. The retrieved evidence is checked for relevance and sufficiency.
6. If sufficient evidence is available, the LLM generates an evidence-based answer with citations.
7. If the evidence is insufficient, the chatbot returns an abstention response instead of guessing.

## 📁 Project Structure

```text
PakKnowledge-AI/
│
├── data/
│   ├── documents/
│   ├── uploads/
│   └── chroma_db/
│
├── ingestion/
│   ├── indexer.py
│   └── load_documents.py
│
├── retrieval/
│   ├── __init__.py
│   └── search.py
│
├── images/
│   ├── desktop-preview.png
│   └── mobile-preview.png
├── app.py
├── graph.py
├── llm_client.py
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

**Note:** The document files and ChromaDB database are stored locally and are excluded from the GitHub repository. The directory structure can be recreated when setting up the project.

## ⚙️ Installation and Setup

### 1. Clone the Repository

```bash
git clone https://github.com/Muntazir-43/PakKnowledge-AI.git
```

Navigate into the project directory:

```bash
cd PakKnowledge-AI
```

### 2. Create a Virtual Environment

```bash
python -m venv .venv
```

Activate it on Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure the Groq API

Create a `.env` file in the project root using `.env.example` as a template.

Add your Groq API key:

```env
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=openai/gpt-oss-20b
```

Replace the placeholder with your own API key.

You can obtain an API key from [Groq Console](https://console.groq.com/).

**Security:** Never upload your `.env` file or expose your API key publicly.

## 📚 Document Ingestion

PakKnowledge AI currently supports the following document formats:

- PDF
- DOCX
- TXT

Place your documents inside the appropriate category folders under:

```text
data/documents/
```

For example:

```text
data/documents/history/
data/documents/geography/
data/documents/economy/
```

Run the indexing process:

```bash
python -m ingestion.indexer
```

The ingestion pipeline processes supported documents, extracts their text, divides the content into chunks, and stores the indexed information in ChromaDB.

The vector database is persisted locally in:

```text
data/chroma_db/
```

## 🚀 Running the Application

After configuring the environment and indexing your documents, start the Streamlit application:

```bash
streamlit run app.py
```

Open the application in your browser:

```text
http://localhost:8501
```

You can now ask questions about Pakistan using the chatbot interface.

## 💬 Example Questions

Here are some example questions you can ask:

| Category | Example Question |
|---|---|
| History | What were the major events leading to the creation of Pakistan? |
| Geography | What are the major geographical features of Pakistan? |
| Government & Laws | What does the Constitution of Pakistan say about fundamental rights? |
| Economy | What are the major sectors of Pakistan's economy? |
| Education | What are the main objectives of Pakistan's Federal Education Policy? |
| Culture | What are some important elements of Pakistan's cultural heritage? |
| Tourism | What activities does Pakistan offer for adventure tourism? |
| Public Services | What information do the indexed documents provide about public services in Pakistan? |

The answers depend on the information available in the indexed knowledge base.

## 🔒 Reliability and Limitations

PakKnowledge AI incorporates evidence verification and abstention mechanisms to improve answer reliability.

- Answers are grounded in retrieved indexed documents.
- Source citations are provided for supported answers.
- Questions outside the intended Pakistan-related scope are declined.
- Questions without sufficient supporting evidence receive an abstention response.

**Current limitations:**

- Only PDF, DOCX, and TXT document ingestion is implemented.
- Website URL ingestion and live web retrieval are not currently supported.
- Answer quality depends on the relevance, coverage, and quality of indexed documents.
- The knowledge base must be populated and indexed locally before meaningful answers can be generated.
- This is an MVP project and has not been designed as a fully production-scale service.

## 🔮 Future Improvements

Potential future enhancements include:

- Website URL ingestion and web-based retrieval.
- Improved document retrieval and ranking.
- Expanded and regularly updated Pakistan-related knowledge sources.
- Additional evaluation datasets and automated testing.
- Deployment as an online application.

These are planned improvements, not currently implemented features.

## 👨‍💻 Author

**Muntazir Mehdi**

GitHub: [@Muntazir-43](https://github.com/Muntazir-43)

## 📄 License

A license has not yet been selected for this repository. Please check the repository for licensing information before reusing or distributing the project.
