# Docs site (GitHub Pages)

Static, dependency-free documentation site. Everything runs client-side: `app.js` fetches the Markdown files from `content/` and renders them (own mini renderer, no CDN, no build step).

## Enable GitHub Pages

1. Push the repo to GitHub.
2. Repo **Settings → Pages**.
3. Source: **Deploy from a branch** → branch `main` (or `master`), folder **`/docs`** → Save.
4. The site goes live at `https://<user>.github.io/<repo>/`.

## Updating content

The files in `content/` are copies of the repo docs. When a doc changes, re-copy it:

| Site page | Source file |
|---|---|
| `readme.{en,pt}.md` | `README.{en,pt}.md` |
| `scripting.{en,pt}.md` | `DOCS.{en,pt}.md` |
| `lua-api.{en,pt}.md` | `Backend/LUA_API.{en,pt}.md` |
| `configuration.{en,pt}.md` | `Backend/CONFIGURATION.{en,pt}.md` |
| `protocol.{en,pt}.md` | `UI/AutoUI/README.md` |
| `changelog.{en,pt}.md` | `CHANGELOG.md` |

Adding a page: drop `name.en.md` + `name.pt.md` in `content/` and add an entry to `PAGES` in `app.js`.

Edit the GitHub/NexusMods links in the sidebar footer of `index.html`.

## Test locally

```bash
cd docs
python -m http.server 8000
# open http://localhost:8000
```
