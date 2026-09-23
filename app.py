import os
import re
import uuid
import threading
import time

from flask import Flask, render_template, request, jsonify, send_from_directory, abort
import yt_dlp

app = Flask(__name__)

DOWNLOAD_DIR = os.path.join(os.path.dirname(__file__), "downloads")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# Very small in-memory job store: {job_id: {"status": ..., "filename": ..., "title": ..., "error": ...}}
JOBS = {}
JOB_LOCK = threading.Lock()

INSTAGRAM_URL_RE = re.compile(
    r"^https?://(www\.)?instagram\.com/(p|reel|tv)/[A-Za-z0-9_\-]+/?.*$"
)


def is_valid_instagram_url(url: str) -> bool:
    return bool(INSTAGRAM_URL_RE.match(url.strip()))


def cleanup_old_files(max_age_seconds=3600):
    """Remove downloaded files older than max_age_seconds to avoid filling disk."""
    now = time.time()
    for fname in os.listdir(DOWNLOAD_DIR):
        fpath = os.path.join(DOWNLOAD_DIR, fname)
        try:
            if os.path.isfile(fpath) and now - os.path.getmtime(fpath) > max_age_seconds:
                os.remove(fpath)
        except OSError:
            pass


def run_download(job_id: str, url: str):
    """Background worker: extracts and downloads the video via yt-dlp."""
    cleanup_old_files()
    out_template = os.path.join(DOWNLOAD_DIR, f"{job_id}.%(ext)s")

    ydl_opts = {
        "outtmpl": out_template,
        "format": "mp4/best",
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        # If you need to download private/age-restricted content, point this
        # at a Netscape-format cookies file exported from your browser:
        # "cookiefile": "cookies.txt",
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            filename = os.path.basename(filename)
            title = info.get("title") or "instagram_video"

        with JOB_LOCK:
            JOBS[job_id] = {
                "status": "done",
                "filename": filename,
                "title": title,
                "error": None,
            }
    except Exception as e:
        with JOB_LOCK:
            JOBS[job_id] = {
                "status": "error",
                "filename": None,
                "title": None,
                "error": str(e),
            }


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/start", methods=["POST"])
def start_download():
    data = request.get_json(silent=True) or {}
    url = (data.get("url") or "").strip()

    if not url:
        return jsonify({"error": "Please provide an Instagram URL."}), 400
    if not is_valid_instagram_url(url):
        return jsonify({"error": "That doesn't look like a valid Instagram post/reel URL."}), 400

    job_id = uuid.uuid4().hex
    with JOB_LOCK:
        JOBS[job_id] = {"status": "processing", "filename": None, "title": None, "error": None}

    thread = threading.Thread(target=run_download, args=(job_id, url), daemon=True)
    thread.start()

    return jsonify({"job_id": job_id})


@app.route("/api/status/<job_id>")
def status(job_id):
    with JOB_LOCK:
        job = JOBS.get(job_id)
    if not job:
        return jsonify({"error": "Unknown job id."}), 404
    return jsonify(job)


@app.route("/download/<job_id>")
def download_file(job_id):
    with JOB_LOCK:
        job = JOBS.get(job_id)
    if not job or job["status"] != "done" or not job["filename"]:
        abort(404)
    return send_from_directory(
        DOWNLOAD_DIR,
        job["filename"],
        as_attachment=True,
        download_name=f"{job['title'][:60]}.mp4",
    )


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
