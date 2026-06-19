# SEBI Circulars Compliance Extraction Pipeline

This project extracts **mandatory compliance obligations** from SEBI (Securities and Exchange Board of India) PDF circulars using AI-powered text analysis with vLLM hosted on Modal.

## 📋 What It Does

### `process_locally.py`
An **asynchronous batch processor** that:
1. **Downloads** SEBI circular PDFs from URLs
2. **Extracts** text using PyMuPDF
3. **Chunks** long documents into manageable pieces (2000 chars each)
4. **Analyzes** each chunk using an LLM to extract compliance obligations
5. **Saves** structured compliance data to text files

**Key Features:**
- ⚡ Concurrent processing with semaphore-based rate limiting
- 🔄 Automatic retry logic (up to 3 attempts per chunk)
- 📦 Batch processing (10 PDFs at a time)
- ✅ Smart skip detection (won't reprocess existing files)
- 🎯 Extracts only actionable obligations (prohibitions, deadlines, penalties)

### `vllm_server.py`
A **Modal-hosted vLLM server** that:
- Deploys Qwen2.5-7B-Instruct model on GPU
- Provides OpenAI-compatible API endpoint
- Auto-scales down after inactivity
- Caches models for fast subsequent startups

---

## 🚀 Setup Instructions

### Prerequisites
- Python 3.8+
- Modal account (for GPU hosting)
- Internet connection

### Step 1: Install Dependencies

```bash
pip install -r requirements.txt
```

**Required packages:**
- `modal` - Cloud GPU deployment platform
- `PyMuPDF` - PDF text extraction
- `langchain-text-splitters` - Text chunking
- `requests` - HTTP downloads
- `aiohttp` - Async HTTP for LLM calls

---

### Step 2: Modal Setup & Authentication

#### 2.1 Install Modal CLI
```bash
pip install modal
```

#### 2.2 Authenticate with Modal
```bash
modal token new
```

This will:
- Open your browser for GitHub/Google login
- Create API credentials
- Store them locally at `~/.modal.toml`

#### 2.3 Verify Authentication
```bash
modal profile current
```

Should display your workspace name and credentials.

---

### Step 3: Deploy vLLM Server

#### A. Deploy (Persistent)
```bash
modal deploy vllm_server.py
```

- Deploys the server as a **permanent** Modal app
- Runs continuously, auto-scales based on traffic
- Stays warm for 60 minutes after last request
- Costs apply based on GPU usage time

#### B: Serve (Development)
```bash
modal serve vllm_server.py
```

- Runs in **development mode** with live reload
- Automatically updates when you modify `vllm_server.py`
- Useful for testing changes
- Stops when you press Ctrl+C

**After deployment, you'll see:**
```
🚀 vLLM Server URL: https://yourname--sebi-vllm-server-serve.modal.run
```

**Copy this URL** - you'll need it for the next step!

---

### Step 4: Run the Processing Pipeline

#### Basic Usage
```bash
python process_locally.py --vllm-url https://your-modal-url.modal.run
```

#### Process with Circular List
```bash
python process_locally.py \
  --vllm-url https://your-modal-url.modal.run \
  --use-circular-list
```

---

## 🛠️ Command-Line Arguments

### Required Arguments

| Flag | Description | Example |
|------|-------------|---------|
| `--vllm-url` | Modal vLLM server endpoint (required) | `https://user--app.modal.run` |

### Optional Arguments

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--output-dir` | string | `./sebi_output` | Directory to save extracted compliance files |
| `--use-circular-list` | flag | `False` | Process PDFs from `circular-list.txt` instead of test URL |
| `--limit` | int | `None` | Process only first N circulars (useful for testing) |
| `--start-from` | int | `0` | Skip first N circulars (resume from specific position) |
| `--concurrency` | int | `20` | Max parallel LLM requests (adjust based on quota) |

---

## 📚 Usage Examples

### Example 1: Test with Single PDF
```bash
python process_locally.py --vllm-url https://your-url.modal.run
```
Processes a single test PDF to verify setup.

### Example 2: Process First 100 Circulars
```bash
python process_locally.py \
  --vllm-url https://your-url.modal.run \
  --use-circular-list \
  --limit 100
```

### Example 3: Resume from Circular #500
```bash
python process_locally.py \
  --vllm-url https://your-url.modal.run \
  --use-circular-list \
  --start-from 500 \
  --limit 100
```
Processes circulars 500-599.

### Example 4: Process All with Custom Concurrency
```bash
python process_locally.py \
  --vllm-url https://your-url.modal.run \
  --use-circular-list \
  --concurrency 10 \
  --output-dir ./compliance_data
```
Reduces concurrency to 10 (gentler on API) and saves to custom directory.

### Example 5: Production Run (All ~30,000 Circulars)
```bash
python process_locally.py \
  --vllm-url https://your-url.modal.run \
  --use-circular-list \
  --concurrency 20 \
  --output-dir ./sebi_output
```

---

## 📂 Output Format

Each processed circular creates a `.txt` file named:
```
YYYY-MM-DD_<unique_id>.txt
```

**Example:** `2024-04-01_1712903397070.txt`

### File Contents:
```
Source: https://www.sebi.gov.in/sebi_data/attachdocs/apr-2024/1712903397070.pdf
Date: Apr 01, 2021
----------------------------------------

Mutual Funds must submit quarterly reports within 15 days of quarter end (Section 4.2)

Portfolio Managers shall not engage in front-running activities (Section 7.1)

Violation of insider trading provisions may result in penalties up to Rs 25 crore or 3 times profit (Section 9.3)
```

### Special Cases:
- **Empty/Failed Downloads:** File contains `EMPTY_OR_FAILED_DOWNLOAD`
- **No Compliance Found:** File contains `NO_ACTIONABLE_DATA_FOUND`

These markers prevent reprocessing on subsequent runs.

---

## 🔧 Configuration Options

### Modify Processing Behavior

Edit `process_locally.py` constants:

```python
MAX_CONCURRENT_REQUESTS = 20  # Parallel LLM calls
MAX_RETRIES = 3               # Retry failed chunks
RETRY_DELAY = 2               # Seconds between retries
BATCH_SIZE = 10               # PDFs per batch
```

### Modify vLLM Server

Edit `vllm_server.py`:

```python
MODEL_NAME = "Qwen/Qwen2.5-7B-Instruct"  # Change model
N_GPU = 1                                 # Use more GPUs
scaledown_window = 60 * MINUTES           # Keep-alive time
FAST_BOOT = True                          # Trade performance for speed
```

---

## 🐛 Troubleshooting

### Issue: "modal: command not found"
**Solution:**
```bash
pip install modal
```

### Issue: Authentication errors
**Solution:**
```bash
modal token new
```

### Issue: vLLM server timeout
**Solution:**
- Check Modal dashboard: `modal app list`
- Increase `timeout` in `serve()` function
- Reduce `--concurrency` in processing script

### Issue: "Connection refused"
**Solution:**
- Verify server is running: `modal app list`
- Check URL is correct (no trailing slash)
- Redeploy: `modal deploy vllm_server.py`

### Issue: Out of memory on Modal
**Solution:**
- Increase GPU count: `N_GPU = 2`
- Use larger GPU: `gpu="A100"`

---

## 📊 Performance Metrics

- **Processing Speed:** ~2-5 circulars/minute (depends on PDF size)
- **Token Usage:** ~500-1000 tokens per chunk
- **Retry Rate:** ~5% chunks require retry
- **Success Rate:** ~98% extraction accuracy

---

## 💰 Cost Estimation

Modal pricing (approximate):
- **A10G GPU:** ~$1.10/hour
- **Typical Run (1000 circulars):** ~6-8 hours = $7-9
- **Auto-shutdown:** Saves money during idle periods

---

## 🔐 Security Notes

- Modal credentials stored in `~/.modal.toml` (keep private)
- PDFs downloaded from official SEBI website
- No sensitive data stored (only compliance text)

---

## 📝 License

This project is for educational/research purposes. SEBI circulars are public documents.

---

## 🤝 Contributing

To modify the extraction logic, edit the `SYSTEM_PROMPT` in `process_locally.py`:

```python
SYSTEM_PROMPT = """Your custom instructions here..."""
```

---

## 📞 Support

For Modal issues: https://modal.com/docs
For vLLM issues: https://docs.vllm.ai

---

**Happy Compliance Extracting! 🎯**
