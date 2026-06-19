# Installation Guide

## Quick Start

### 1. Install Dependencies

Using pip:
```bash
pip install -e .
```

Or using requirements.txt:
```bash
pip install -r requirements.txt
```

### 2. Post-Installation Steps

#### Install spaCy Language Model
The smart news scraper requires the English language model for NER:

```bash
python -m spacy download en_core_web_sm
```

#### Download NLTK Data
TextBlob and newspaper3k require NLTK data:

```python
python -c "import nltk; nltk.download('punkt'); nltk.download('brown'); nltk.download('wordnet')"
```

Or interactively:
```python
import nltk
nltk.download('punkt')
nltk.download('brown')
nltk.download('wordnet')
```

### 3. Environment Variables

Create a `.env` file in the project root:

```bash
# Required
OPENAI_API_KEY=your-openai-api-key

# Optional but recommended
NEWSDATA_API_KEY=your-newsdata-api-key  # For smart news scraper
SERPAPI_KEY=your-serpapi-key  # For web search

# Optional
GROQ_API_KEY=your-groq-api-key  # For guardrails (Llama Guard)
```

### 4. Verify Installation

Test the smart news scraper:
```bash
python tests/test_smart_news_scraper_integration.py
```

## Optional: GPU Support for Transformers

If you have a CUDA-compatible GPU and want faster sentiment analysis:

```bash
# Install PyTorch with CUDA support
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

The smart news scraper will automatically use GPU if available.

## Troubleshooting

### spaCy Model Not Found
If you see: `OSError: [E050] Can't find model 'en_core_web_sm'`
```bash
python -m spacy download en_core_web_sm
```

### Transformers Model Download
FinBERT model will be downloaded automatically on first use (~500MB).
Make sure you have internet connection.

### NLTK Data Missing
If you see NLTK errors:
```python
import nltk
nltk.download('all')  # Downloads all NLTK data
```

### Memory Issues
If you encounter memory issues with transformers:
- The FinBERT model uses ~500MB RAM
- Consider using CPU mode if GPU memory is limited
- Reduce `max_articles` parameter in news scraping

## Dependencies Overview

### Core Dependencies
- **LangChain & LangGraph**: Agent orchestration
- **OpenAI**: LLM API
- **Streamlit**: Web UI

### News Scraping
- **newsdataapi**: News API client
- **newspaper3k**: Article extraction
- **transformers**: FinBERT sentiment analysis
- **spacy**: Named Entity Recognition
- **beautifulsoup4**: HTML parsing

### Web Search
- **google-search-results**: SerpAPI client

### Data Processing
- **pandas**: Data manipulation
- **numpy**: Numerical computing
- **scikit-learn**: Machine learning utilities

### Other
- **chromadb**: Vector database for RAG
- **pydantic**: Data validation
- **plotly**: Visualizations

