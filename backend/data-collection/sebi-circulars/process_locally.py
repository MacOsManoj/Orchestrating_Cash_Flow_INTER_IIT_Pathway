import asyncio
import aiohttp
import requests
import os
import re
from pathlib import Path
import fitz  # PyMuPDF
from langchain_text_splitters import RecursiveCharacterTextSplitter
import argparse
from datetime import datetime
import time

# --- CONFIGURATION ---
MAX_CONCURRENT_REQUESTS = 20
MAX_RETRIES = 3  # Retry failed vLLM calls up to 3 times
RETRY_DELAY = 2  # Seconds to wait between retries

# --- OPTIMIZED PROMPT ---
SYSTEM_PROMPT = """You are a strict compliance extraction engine. 
Analyze the text and extract **MANDATORY** compliance obligations, prohibitions, penalties, or numerical limits.

TARGET INFORMATION:
1. Hard Requirements (must, shall, required to).
2. Prohibitions (shall not, prohibited).
3. Penalties (fines, imprisonment).
4. Deadlines or Numerical Limits.

OUTPUT FORMAT:
- If NO actionable obligations are found, output exactly: N/A
- If found, list them as clear sentences.
- Format: <Entity> must/shall <Action> <Deadline/Constraint> (Section <Ref>)

RULES:
- Do NOT use square brackets [ ].
- Do NOT output headers.
- Only output the final extracted facts."""


def load_circulars_from_file(
    file_path: str = "circular-list.txt",
) -> list[tuple[str, str]]:
    circulars = []
    if not os.path.exists(file_path):
        return []
    with open(file_path, "r") as f:
        for line in f:
            if "|" in line:
                parts = line.split("|")
                circulars.append((parts[0].strip(), parts[1].strip()))
    return circulars[::-1]


def date_to_filename(date_str: str, pdf_url: str) -> str:
    match = re.search(r"/(\d+)\.pdf", pdf_url)
    unique_id = match.group(1) if match else pdf_url.split("/")[-1].replace(".pdf", "")
    try:
        dt = datetime.strptime(date_str, "%b %d, %Y")
        date_part = dt.strftime("%Y-%m-%d")
    except:
        date_part = date_str.replace(" ", "_").replace(",", "")
    return f"{date_part}_{unique_id}"


def download_and_extract(url: str, idx: int) -> str:
    """Synchronous download with strict timeout."""
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        # Added strict timeout for download (10s connect, 30s read)
        resp = requests.get(url, headers=headers, timeout=(10, 30))
        resp.raise_for_status()

        doc = fitz.open(stream=resp.content, filetype="pdf")
        text = "\n".join([page.get_text() for page in doc])
        doc.close()
        return text
    except Exception as e:
        print(f"❌ [{idx}] Failed to extract: {e}")
        return ""


def chunk_text(text: str) -> list[str]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=2000,
        chunk_overlap=200,
        separators=["\n\n", "\n", ". "],
    )
    return splitter.split_text(text)


async def process_chunk(
    session: aiohttp.ClientSession,
    chunk: str,
    chunk_idx: int,
    total_chunks: int,
    pdf_idx: int,
    semaphore: asyncio.Semaphore,
    vllm_url: str,
) -> str:
    """Process a chunk with RETRY logic."""
    async with semaphore:
        payload = {
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": chunk},
            ],
            "model": "llm",
            "temperature": 0.1,
            "max_tokens": 512,
        }

        # --- RETRY LOGIC ADDED HERE ---
        for attempt in range(MAX_RETRIES):
            try:
                # Per-request timeout (prevent hanging forever)
                async with session.post(
                    f"{vllm_url}/v1/chat/completions", json=payload, timeout=45
                ) as resp:
                    if resp.status != 200:
                        if attempt < MAX_RETRIES - 1:
                            await asyncio.sleep(RETRY_DELAY)
                            continue
                        return None

                    result = await resp.json()
                    content = result["choices"][0]["message"]["content"].strip()

                    print(
                        f"    ↳ [{pdf_idx}] Chunk {chunk_idx}/{total_chunks} completed"
                    )

                    if content in ["N/A", "None", "No actionable obligations found."]:
                        return None
                    if "N/A" in content[:5]:
                        return None

                    return content

            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                if attempt < MAX_RETRIES - 1:
                    print(
                        f"    ⚠️ [{pdf_idx}] Chunk {chunk_idx} timed out/failed (Attempt {attempt + 1}). Retrying..."
                    )
                    await asyncio.sleep(RETRY_DELAY)
                else:
                    print(
                        f"    ❌ [{pdf_idx}] Chunk {chunk_idx} GAVE UP after {MAX_RETRIES} attempts."
                    )
                    return None
            except Exception as e:
                print(f"    ❌ [{pdf_idx}] Critical Error: {e}")
                return None
        return None


async def process_single_pdf_flow(
    session: aiohttp.ClientSession,
    semaphore: asyncio.Semaphore,
    vllm_url: str,
    pdf_data: tuple,
    output_dir: Path,
    idx: int,
):
    date_str, url = pdf_data
    filename = f"{date_to_filename(date_str, url)}.txt"
    output_file = output_dir / filename

    # SKIP CHECK: Even if the file is empty (marked as "N/A"), we skip it
    if output_file.exists():
        print(f"⏭️  [{idx}] Skipping {filename} (Already Processed)")
        return

    # 1. Download
    start_time = time.time()
    text = await asyncio.to_thread(download_and_extract, url, idx)

    # If download fails or text is empty, create an EMPTY marker file so we don't retry next time
    if not text or len(text) < 50:
        print(f"⚠️ [{idx}] Text empty. Marking as processed.")
        with open(output_file, "w") as f:
            f.write("EMPTY_OR_FAILED_DOWNLOAD")
        return

    # 2. Chunk
    chunks = chunk_text(text)
    total_chunks = len(chunks)
    print(f"📄 [{idx}] {filename} | Length: {len(text)} | Chunks: {total_chunks}")

    # 3. Process
    tasks = [
        process_chunk(session, c, i + 1, total_chunks, idx, semaphore, vllm_url)
        for i, c in enumerate(chunks)
    ]
    results = await asyncio.gather(*tasks)

    # 4. Save
    valid_results = [r for r in results if r]
    duration = time.time() - start_time

    if valid_results:
        print(f"💾 [{idx}] Saving {len(valid_results)} extracted points -> {filename}")
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(f"Source: {url}\nDate: {date_str}\n{'-' * 40}\n\n")
            f.write("\n\n".join(valid_results))
    else:
        # --- IMPORTANT: CREATE MARKER FILE ---
        # Writes a placeholder file so next run detects it as "done"
        print(f"ℹ️  [{idx}] No data found. creating marker file.")
        with open(output_file, "w", encoding="utf-8") as f:
            f.write("NO_ACTIONABLE_DATA_FOUND")


async def main(args):
    output_path = Path(args.output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    if args.use_circular_list:
        circulars = load_circulars_from_file()
        print(f"📋 Loaded {len(circulars)} circulars")
    else:
        circulars = [
            (
                "Test Date",
                "https://www.sebi.gov.in/sebi_data/attachdocs/apr-2024/1712903397070.pdf",
            )
        ]

    if args.start_from:
        circulars = circulars[args.start_from :]
    if args.limit:
        circulars = circulars[: args.limit]

    BATCH_SIZE = 10
    print(f"🚀 Starting | Files: {len(circulars)} | Batch Size: {BATCH_SIZE}")

    semaphore = asyncio.Semaphore(args.concurrency)
    # Session timeout covers the whole batch lifecycle
    timeout = aiohttp.ClientTimeout(total=600)

    async with aiohttp.ClientSession(timeout=timeout) as session:
        for i in range(0, len(circulars), BATCH_SIZE):
            batch = circulars[i : i + BATCH_SIZE]
            batch_num = (i // BATCH_SIZE) + 1

            print(f"\n📦 BATCH {batch_num} (Files {i + 1}-{i + len(batch)})")
            print(f"{'-' * 60}")

            batch_tasks = [
                process_single_pdf_flow(
                    session, semaphore, args.vllm_url, pdf, output_path, i + idx + 1
                )
                for idx, pdf in enumerate(batch)
            ]

            await asyncio.gather(*batch_tasks)
            print(f"✅ BATCH {batch_num} DONE.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--vllm-url", required=True)
    parser.add_argument("--output-dir", default="./sebi_output")
    parser.add_argument("--use-circular-list", action="store_true")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--start-from", type=int, default=0)
    parser.add_argument("--concurrency", type=int, default=20)

    args = parser.parse_args()
    asyncio.run(main(args))
