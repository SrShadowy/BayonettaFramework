/* Bayonetta Trainer V2 — docs site. No dependencies. */
"use strict";

/* ------------------------------------------------------------------ pages */
const PAGES = [
  { id: "readme",        en: "Getting Started",        pt: "Instalação" },
  { id: "scripting",     en: "Config & Scripting",     pt: "Configuração & Scripts" },
  { id: "lua-api",       en: "Lua API Reference",      pt: "Referência da API Lua" },
  { id: "configuration", en: "trainer.ini Reference",  pt: "Referência do trainer.ini" },
  { id: "protocol",      en: "UI Protocol / AutoUI",   pt: "Protocolo da UI / AutoUI" },
  { id: "changelog",     en: "Changelog",              pt: "Changelog" }
];

/* map original repo filenames -> page ids (for links inside the docs) */
const FILE_MAP = {
  "readme.md": "readme", "readme.en.md": "readme", "readme.pt.md": "readme",
  "docs.en.md": "scripting", "docs.pt.md": "scripting",
  "lua_api.md": "lua-api", "lua_api.en.md": "lua-api", "lua_api.pt.md": "lua-api",
  "configuration.md": "configuration", "configuration.en.md": "configuration", "configuration.pt.md": "configuration",
  "changelog.md": "changelog", "changelog.txt": "changelog"
};

const UI_TEXT = {
  en: { toc: "On this page", notfound: "Page not found." },
  pt: { toc: "Nesta página", notfound: "Página não encontrada." }
};

let cur = { lang: "en", page: "readme" };
const cache = {};

/* ------------------------------------------------------------- tiny utils */
const $ = (s) => document.querySelector(s);
const esc = (s) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

/* GitHub-style heading slugs: keep letters/numbers/underscore/hyphen,
   strip other punctuation, each space becomes one hyphen (no collapsing). */
function slug(text) {
  return text
    .replace(/<[^>]*>/g, "")
    .toLowerCase()
    .trim()
    .replace(/[`*~]/g, "")
    .replace(/[^\p{L}\p{N}\s_-]/gu, "")
    .replace(/\s/g, "-");
}

/* -------------------------------------------------------------- md inline */
function fixHref(href) {
  href = href.trim();
  if (/^#/.test(href)) return `#/${cur.lang}/${cur.page}/${href.slice(1)}`;
  const md = href.match(/([^/\\)]+\.(?:md|txt))(?:[#?].*)?$/i);
  if (md) {
    const id = FILE_MAP[md[1].toLowerCase()];
    if (id) {
      const lang = /\.pt\.(md|txt)$/i.test(md[1]) ? "pt" : /\.en\.(md|txt)$/i.test(md[1]) ? "en" : cur.lang;
      return `#/${lang}/${id}`;
    }
  }
  return href;
}

function inline(text) {
  const codes = [];
  text = text.replace(/`([^`]+)`/g, (m, c) => {
    codes.push(c);
    return "\u0000" + (codes.length - 1) + "\u0000";
  });
  text = esc(text);
  text = text.replace(/!\[([^\]]*)\]\(([^)\s]+)\)/g, '<img alt="$1" src="$2">');
  text = text.replace(/\[([^\]]+)\]\(([^)]+)\)/g, (m, t, h) => {
    const url = fixHref(h);
    const ext = /^https?:\/\//i.test(url) ? ' target="_blank" rel="noopener"' : "";
    return `<a href="${url}"${ext}>${t}</a>`;
  });
  text = text.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
  text = text.replace(/__([^_]+)__/g, "<strong>$1</strong>");
  text = text.replace(/(^|[\s(>])\*([^*\n]+)\*/g, "$1<em>$2</em>");
  text = text.replace(/~~([^~]+)~~/g, "<del>$1</del>");
  return text.replace(/\u0000(\d+)\u0000/g, (m, i) => `<code>${esc(codes[+i])}</code>`);
}

/* -------------------------------------------------------------- md blocks */
function mdToHtml(src) {
  const lines = src.replace(/\r\n?/g, "\n").split("\n");
  const out = [];
  const usedIds = {};
  let i = 0;

  const isListLine = (l) => /^(\s*)([*+-]|\d+[.)])\s+/.test(l);
  const isTableSep = (l) => /^\s*\|?[\s:|-]+\|[\s:|-]*\s*$/.test(l) && l.includes("-");

  function headingId(text) {
    let id = slug(text) || "section";
    if (usedIds[id] != null) id += "-" + ++usedIds[id];
    else usedIds[id] = 0;
    return id;
  }

  while (i < lines.length) {
    const line = lines[i];

    if (/^\s*$/.test(line)) { i++; continue; }

    /* fenced code */
    const fence = line.match(/^\s*```(\w*)/);
    if (fence) {
      const buf = [];
      i++;
      while (i < lines.length && !/^\s*```/.test(lines[i])) buf.push(lines[i++]);
      i++;
      out.push(`<pre><code class="lang-${fence[1] || "text"}">${esc(buf.join("\n"))}</code></pre>`);
      continue;
    }

    /* heading */
    const h = line.match(/^(#{1,6})\s+(.*)$/);
    if (h) {
      const level = h[1].length;
      const content = inline(h[2].trim());
      out.push(`<h${level} id="${headingId(h[2])}">${content}</h${level}>`);
      i++;
      continue;
    }

    /* hr */
    if (/^\s*(-{3,}|\*{3,}|_{3,})\s*$/.test(line)) { out.push("<hr>"); i++; continue; }

    /* blockquote / callout */
    if (/^\s*>/.test(line)) {
      const buf = [];
      while (i < lines.length && /^\s*>/.test(lines[i])) buf.push(lines[i++].replace(/^\s*> ?/, ""));
      let type = null;
      const first = buf[0] && buf[0].match(/^\[!(NOTE|TIP|IMPORTANT|WARNING|CAUTION)\]\s*(.*)/i);
      if (first) { type = first[1].toLowerCase(); buf[0] = first[2]; }
      const innerHtml = mdToHtml(buf.join("\n"));
      if (type) {
        out.push(`<div class="callout ${type}"><span class="callout-label">${type}</span>${innerHtml}</div>`);
      } else {
        out.push(`<blockquote>${innerHtml}</blockquote>`);
      }
      continue;
    }

    /* table */
    if (line.includes("|") && i + 1 < lines.length && isTableSep(lines[i + 1])) {
      const cells = (l) => l.trim().replace(/^\|/, "").replace(/\|\s*$/, "").split("|").map((c) => inline(c.trim()));
      const head = cells(line);
      i += 2;
      const rows = [];
      while (i < lines.length && lines[i].includes("|") && !/^\s*$/.test(lines[i])) rows.push(cells(lines[i++]));
      let html = "<table><thead><tr>" + head.map((c) => `<th>${c}</th>`).join("") + "</tr></thead><tbody>";
      for (const r of rows) html += "<tr>" + r.map((c) => `<td>${c}</td>`).join("") + "</tr>";
      out.push(html + "</tbody></table>");
      continue;
    }

    /* list */
    if (isListLine(line)) {
      const items = [];
      while (i < lines.length) {
        const l = lines[i];
        if (/^\s*$/.test(l)) {
          if (i + 1 < lines.length && (isListLine(lines[i + 1]) || /^\s{2,}\S/.test(lines[i + 1]))) { i++; continue; }
          break;
        }
        const m = l.match(/^(\s*)([*+-]|\d+[.)])\s+(.*)$/);
        if (m) items.push({ indent: m[1].length, ordered: /\d/.test(m[2]), text: m[3] });
        else if (/^\s+\S/.test(l) && items.length) items[items.length - 1].text += " " + l.trim();
        else break;
        i++;
      }
      out.push(buildList(items, 0));
      continue;
    }

    /* paragraph */
    const buf = [line];
    i++;
    while (
      i < lines.length && !/^\s*$/.test(lines[i]) && !/^(#{1,6})\s/.test(lines[i]) &&
      !isListLine(lines[i]) && !/^\s*>/.test(lines[i]) && !/^\s*```/.test(lines[i]) &&
      !/^\s*(-{3,}|\*{3,})\s*$/.test(lines[i]) &&
      !(lines[i].includes("|") && i + 1 < lines.length && isTableSep(lines[i + 1]))
    ) buf.push(lines[i++]);
    out.push(`<p>${inline(buf.join(" "))}</p>`);
  }
  return out.join("\n");
}

function buildList(items, start) {
  if (!items.length) return "";
  const base = items[0].indent;
  const ordered = items[0].ordered;
  let html = ordered ? "<ol>" : "<ul>";
  for (let j = 0; j < items.length; j++) {
    if (items[j].indent <= base) {
      /* collect children (deeper indent) */
      let end = j + 1;
      while (end < items.length && items[end].indent > base) end++;
      const children = items.slice(j + 1, end);
      html += `<li>${inline(items[j].text)}${children.length ? buildList(children, 0) : ""}</li>`;
      j = end - 1;
    }
  }
  return html + (ordered ? "</ol>" : "</ul>");
}

/* ---------------------------------------------------------------- routing */
function parseHash() {
  const parts = location.hash.replace(/^#\/?/, "").split("/");
  const lang = parts[0] === "pt" ? "pt" : "en";
  const page = PAGES.some((p) => p.id === parts[1]) ? parts[1] : "readme";
  return { lang, page, anchor: parts.slice(2).join("/") || null };
}

async function route() {
  const { lang, page, anchor } = parseHash();
  const changed = lang !== cur.lang || page !== cur.page;
  cur = { lang, page };
  if (changed || !$("#article").dataset.loaded) await loadPage();
  renderNav();
  if (anchor) {
    const el = document.getElementById(anchor);
    if (el) el.scrollIntoView();
  } else if (changed) {
    window.scrollTo(0, 0);
  }
}

async function loadPage() {
  const art = $("#article");
  const key = `${cur.page}.${cur.lang}`;
  try {
    if (!cache[key]) {
      const res = await fetch(`content/${cur.page}.${cur.lang}.md`);
      if (!res.ok) throw new Error(res.status);
      cache[key] = await res.text();
    }
    art.innerHTML = mdToHtml(cache[key]);
    art.dataset.loaded = "1";
    addCopyButtons(art);
    buildToc(art);
    const p = PAGES.find((p) => p.id === cur.page);
    document.title = `${p[cur.lang]} — Bayonetta Trainer V2`;
  } catch (e) {
    art.innerHTML = `<p>${UI_TEXT[cur.lang].notfound}</p>`;
    $("#toc").innerHTML = "";
  }
  $("#sidebar").classList.remove("open");
}

/* ------------------------------------------------------------------- ui */
function renderNav() {
  $("#nav").innerHTML = PAGES.map(
    (p) => `<a href="#/${cur.lang}/${p.id}" class="${p.id === cur.page ? "active" : ""}">${p[cur.lang]}</a>`
  ).join("");
  document.querySelectorAll("#lang-switch button").forEach((b) =>
    b.classList.toggle("active", b.dataset.lang === cur.lang)
  );
  $("#toc-title").textContent = UI_TEXT[cur.lang].toc;
  document.documentElement.lang = cur.lang === "pt" ? "pt-BR" : "en";
}

function buildToc(art) {
  const hs = art.querySelectorAll("h2, h3");
  $("#toc").innerHTML = Array.from(hs)
    .map((h) => `<a href="#/${cur.lang}/${cur.page}/${h.id}" class="toc-${h.tagName.toLowerCase()}">${h.textContent}</a>`)
    .join("");
}

function addCopyButtons(art) {
  art.querySelectorAll("pre").forEach((pre) => {
    const btn = document.createElement("button");
    btn.className = "copy-btn";
    btn.textContent = "copy";
    btn.onclick = () => {
      navigator.clipboard.writeText(pre.querySelector("code").textContent).then(() => {
        btn.textContent = "copied!";
        setTimeout(() => (btn.textContent = "copy"), 1200);
      });
    };
    pre.appendChild(btn);
  });
}

/* ----------------------------------------------------------------- init */
document.querySelectorAll("#lang-switch button").forEach((b) => {
  b.onclick = () => { location.hash = `#/${b.dataset.lang}/${cur.page}`; };
});
$("#menu-btn").onclick = () => $("#sidebar").classList.toggle("open");
window.addEventListener("hashchange", route);
route();
