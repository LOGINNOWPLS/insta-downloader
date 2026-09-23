# Instagram Video Downloader (Web App)

A small Flask app that lets you paste an Instagram post/reel URL and download the video.
It uses [yt-dlp](https://github.com/yt-dlp/yt-dlp) on the backend to extract and fetch the
actual video file, so it stays working even as Instagram's page structure changes.

## How it works
1. You paste a public Instagram post/reel URL and click **Download**.
2. The Flask backend kicks off a background job that calls yt-dlp to extract and
   download the underlying MP4.
3. The frontend polls `/api/status/<job_id>` every 1.5s until it's ready.
4. You get a **Save video** button that streams the file to your computer.

## Setup

```bash
cd insta-downloader
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Then open **http://localhost:5000** in your browser.

## Notes & limitations

- **Public content only** by default. Private accounts / age-restricted posts need
  a `cookiefile` (exported from your logged-in browser session via an extension
  like "Get cookies.txt") passed into the `ydl_opts` in `app.py`:
  ```python
  ydl_opts = {
      ...
      "cookiefile": "cookies.txt",
  }
  ```
- **Terms of Service**: downloading content from Instagram may violate their ToS.
  Only download videos you have the right to save (your own content, content
  with explicit permission, or for personal archival of public posts you have
  rights to use). Don't use this to redistribute others' copyrighted work.
- **Watermarks**: Instagram's own video files generally don't carry a visible
  watermark — that's mostly a TikTok-repost issue. If a specific video does
  have a watermark baked in, that's part of the original file and can't be
  cleanly removed without quality loss/reprocessing.
- **File cleanup**: downloaded files older than 1 hour are auto-deleted from
  the `downloads/` folder on each new request to avoid filling up disk space.
- **Multi-platform**: since this runs on yt-dlp, you can extend it to
  TikTok/YouTube/etc. by relaxing the URL validation regex.

## Deploying

For real deployment (not just localhost), run behind a proper WSGI server
(gunicorn/uwsgi) and put it behind Nginx, and consider rate-limiting the
`/api/start` endpoint since each request shells out to yt-dlp.
