const GRID = document.getElementById("news-grid");
const UPDATED_AT = document.getElementById("updated-at");

function timeAgo(isoString) {
  const then = new Date(isoString);
  const diffMs = Date.now() - then.getTime();
  const mins = Math.floor(diffMs / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

function renderArticle(article) {
  const card = document.createElement("article");
  card.className = "card";

  if (article.image) {
    const img = document.createElement("img");
    img.src = article.image;
    img.alt = "";
    img.loading = "lazy";
    img.onerror = () => img.remove();
    card.appendChild(img);
  }

  const body = document.createElement("div");
  body.className = "card-body";
  body.innerHTML = `
    <div class="card-source">${article.source}</div>
    <h2 class="card-title"><a href="${article.link}" target="_blank" rel="noopener noreferrer">${article.title}</a></h2>
    <p class="card-summary">${article.summary || ""}</p>
    <div class="card-time">${timeAgo(article.published)}</div>
  `;
  card.appendChild(body);
  return card;
}

async function loadNews() {
  try {
    const res = await fetch("data/news.json", { cache: "no-store" });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();

    UPDATED_AT.textContent = `Updated ${timeAgo(data.generated_at)} · ${data.article_count} articles`;

    GRID.innerHTML = "";
    if (!data.articles || data.articles.length === 0) {
      GRID.innerHTML = '<p class="error">No articles yet. Run the fetch script to pull the first batch.</p>';
      return;
    }
    for (const article of data.articles) {
      GRID.appendChild(renderArticle(article));
    }
  } catch (err) {
    GRID.innerHTML = `<p class="error">Couldn't load news.json (${err.message}). Run the fetch script first.</p>`;
    UPDATED_AT.textContent = "";
  }
}

loadNews();
