# nightly-player
Player for the Nightly Brief podcast: https://patelary0303.github.io/nightly-player/

- The Listen link carries the script after `#` (`v2.` text format). With an `E:<YYYY-MM-DD>` line, the page
  streams `episodes/<id>.mp3` once it exists and otherwise checks again every 30 seconds.
- Pushing `episodes/<id>.json` to the `claude/episodes` branch runs `.github/workflows/record.yml`, which records it
  with Kokoro (`record.py`), keeps the newest 14 MP3s on the orphan `audio` branch, and redeploys the site.
- `.github/workflows/pages.yml` publishes `index.html` from `main` plus the `audio` branch under `episodes/`.
  Pages must be set to deploy from GitHub Actions.
