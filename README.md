# My News

A small static news site that automatically pulls headlines from public RSS
feeds and screens article images before showing them.

## How it works

- `feeds.json` lists the RSS feeds to pull from. Currently set to: Yeshiva
  World News, Matzav, The Lakewood Scoop (everything from all three), Fox
  News Politics (everything), and Fox News World filtered down to
  Israel-related stories only (see "Sources & topic rules" below).
- `scripts/fetch_news.py` fetches those feeds, extracts each article's
  image, and writes everything to `data/news.json`.
- `scripts/image_filter.py` checks each candidate image before it's allowed
  through — see "About the image filter" below.
- `index.html` / `app.js` / `style.css` are the static site. They just read
  `data/news.json` and render cards. No server needed.
- `.github/workflows/update-news.yml` runs the fetch script automatically
  every hour on GitHub's servers and commits the updated `news.json`, so the
  site refreshes itself with zero maintenance.

## Setup (10 minutes, no API keys needed)

1. Create a new GitHub repository and push this folder to it.
2. In the repo, go to **Settings → Pages**, set "Source" to "Deploy from a
   branch", branch `main`, folder `/ (root)`. Save.
3. Go to the **Actions** tab, find "Update news", and click **Run workflow**
   once to generate the first `data/news.json` (otherwise it'll just run on
   the next hourly schedule).
4. After the workflow finishes (a few minutes — it has to install
   TensorFlow/DeepFace the first time), visit
   `https://<your-username>.github.io/<repo-name>/`.

That's it — from then on it updates itself hourly. Edit the `cron` line in
`.github/workflows/update-news.yml` to change how often (e.g. `*/30 * * * *`
for every 30 minutes).

## Running it locally instead

```bash
pip install -r requirements.txt
python scripts/fetch_news.py   # writes data/news.json
python -m http.server 8000     # then open http://localhost:8000
```

## About the image filter — please read

You asked specifically to filter out images of women. Here's what's
actually implemented, and its real limits:

`image_filter.py` downloads each candidate image and runs it through
[DeepFace](https://github.com/serengil/deepface), an open-source face
detection + gender classification library. Any image where a detected face
is classified as female gets dropped (the article just displays without a
picture instead).

This is a genuine, working filter — but automatic gender classification
from photos is **not reliable**, for anyone building on this kind of
technology:

- It will miss some photos of women — side profiles, partial faces, low
  resolution, sunglasses/hats, unusual crops, etc. all reduce detection
  accuracy.
- It can misfire on illustrations, graphics, or crowd photos.
- These classifiers are known to be less accurate across different
  ethnicities, ages, and gender presentations — this is a documented
  limitation of the field, not specific to this script.

There is no version of this that guarantees zero images of women get
through. If you need a **100% guaranteed** result, the only fully reliable
option is to turn off images entirely — set `ALLOW_ANY_IMAGES = False` at
the top of `scripts/image_filter.py`. Every article will then show as a
text-only card.

You can also tune `ON_UNCERTAIN_IMAGE` (env var, defaults to `"keep"`) to
`"drop"` if you'd rather lose more images than risk one slipping through
undetected.

## Sources & topic rules

Each entry in `feeds.json` can optionally include `include_keywords` and/or
`exclude_keywords` — case-insensitive substring lists checked against each
article's title + summary:

- `include_keywords`: only articles matching at least one keyword are kept
  (everything else from that feed is dropped).
- `exclude_keywords`: articles matching any keyword are dropped, everything
  else is kept.

Current setup:

| Source | Feed | Rule |
|---|---|---|
| Yeshiva World News | `yeshivaworld.com/feed` | everything |
| Matzav | `matzav.com/feed` | everything |
| The Lakewood Scoop | `thelakewoodscoop.com/feed` | everything |
| Fox News Politics | official Fox politics RSS | everything |
| Fox News (Israel) | official Fox world-news RSS | only articles matching Israel-related keywords (israel, gaza, netanyahu, idf, hamas, jerusalem, hezbollah, west bank, knesset, etc.) |

Note on "Fox News, only politics and Israel": Fox doesn't publish a
dedicated "Israel" RSS feed, so Israel coverage is pulled from their World
feed and filtered down by keyword. This means: (a) an Israel story Fox
publishes without any of those keywords in the title/summary could be
missed, and (b) it only filters what Fox's own World feed includes — it
won't pull in Israel coverage from outlets not listed here.

## Customizing

- **Add/remove sources:** edit `feeds.json`. Any standard RSS/Atom feed URL
  works.
- **Add topic rules to a source:** add `include_keywords` (allow-list) or
  `exclude_keywords` (block-list) to that feed's entry in `feeds.json`.
- **Change how many articles show:** `max_articles_per_feed` /
  `max_total_articles` in `feeds.json`.
- **Styling:** edit `style.css`.
