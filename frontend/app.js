const API = "/api";

const grid = document.getElementById("collectionGrid");
const characterRail = document.getElementById("characterRail");
const filterSeries = document.getElementById("filterSeries");
const filterAuthor = document.getElementById("filterAuthor");
const filterStoryline = document.getElementById("filterStoryline");

let activeCharacter = null;

async function loadComics() {
  const params = new URLSearchParams();
  if (activeCharacter) params.set("character", activeCharacter);
  if (filterSeries.value) params.set("series", filterSeries.value);
  if (filterAuthor.value) params.set("author", filterAuthor.value);
  if (filterStoryline.value) params.set("storyline", filterStoryline.value);

  const res = await fetch(`${API}/comics?${params}`);
  const comics = await res.json();
  renderGrid(comics);
}

function renderGrid(comics) {
  grid.innerHTML = "";
  for (const c of comics) {
    const card = document.createElement("div");
    card.className = "comic-card";
    card.innerHTML = `
      <img src="${c.cover_image_url || ''}" alt="${escapeHtml(c.title)}">
      <div class="card-text">
        <p class="card-title">${escapeHtml(c.title)} ${c.issue_number ? '#' + c.issue_number : ''}</p>
        <p class="card-meta">${escapeHtml(c.author || 'Unknown author')}</p>
        <p class="card-meta">${c.cover_date || ''}</p>
      </div>`;
    grid.appendChild(card);
  }
}

async function loadCharacters() {
  const res = await fetch(`${API}/characters`);
  const chars = await res.json();
  characterRail.innerHTML = "";
  for (const ch of chars) {
    const btn = document.createElement("button");
    btn.className = "character-avatar";
    btn.innerHTML = `<img src="${ch.image_url || ''}" alt="${escapeHtml(ch.name)}"><span>${escapeHtml(ch.name)}</span>`;
    btn.onclick = () => {
      activeCharacter = activeCharacter === ch.name ? null : ch.name;
      document.querySelectorAll(".character-avatar").forEach(b => b.classList.remove("active"));
      if (activeCharacter) btn.classList.add("active");
      loadComics();
    };
    characterRail.appendChild(btn);
  }
}

async function loadFilterOptions() {
  const res = await fetch(`${API}/filters`);
  const opts = await res.json();
  fillSelect(filterSeries, opts.series);
  fillSelect(filterAuthor, opts.authors);
  fillSelect(filterStoryline, opts.storylines);
}

function fillSelect(select, values) {
  const current = select.value;
  select.innerHTML = `<option value="">${select.firstElementChild.textContent}</option>`;
  for (const v of values) {
    const opt = document.createElement("option");
    opt.value = v;
    opt.textContent = v;
    select.appendChild(opt);
  }
  select.value = current;
}

[filterSeries, filterAuthor, filterStoryline].forEach(sel =>
  sel.addEventListener("change", loadComics)
);
document.getElementById("clearFilters").onclick = () => {
  activeCharacter = null;
  filterSeries.value = "";
  filterAuthor.value = "";
  filterStoryline.value = "";
  document.querySelectorAll(".character-avatar").forEach(b => b.classList.remove("active"));
  loadComics();
};

// ---------- upload / match modal ----------
const modal = document.getElementById("uploadModal");
const fileInput = document.getElementById("fileInput");
const uploadStatus = document.getElementById("uploadStatus");
const uploadStep = document.getElementById("uploadStep");
const candidateStep = document.getElementById("candidateStep");
const candidateList = document.getElementById("candidateList");

document.getElementById("addBtn").onclick = () => {
  modal.classList.remove("hidden");
  uploadStep.classList.remove("hidden");
  candidateStep.classList.add("hidden");
  uploadStatus.textContent = "";
  fileInput.value = "";
};
document.getElementById("closeModal").onclick = () => modal.classList.add("hidden");

fileInput.addEventListener("change", async () => {
  const file = fileInput.files[0];
  if (!file) return;
  uploadStatus.textContent = "Reading cover…";

  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${API}/upload`, { method: "POST", body: form });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    uploadStatus.textContent = err.detail || "Couldn't process that photo. Try again.";
    return;
  }
  const data = await res.json();
  uploadStatus.textContent = "";
  uploadStep.classList.add("hidden");
  candidateStep.classList.remove("hidden");
  candidateList.innerHTML = "";

  if (data.candidates.length === 0) {
    candidateList.innerHTML = "<p>No matches found — try a clearer photo, or add it manually later.</p>";
  }

  for (const c of data.candidates) {
    const item = document.createElement("div");
    item.className = "candidate-item";
    item.innerHTML = `
      <img src="${c.cover_image_url || ''}" alt="">
      <p>${escapeHtml(c.title)} ${c.issue_number ? '#' + c.issue_number : ''}</p>`;
    item.onclick = () => confirmMatch(c.comicvine_id, data.uploaded_image_path);
    candidateList.appendChild(item);
  }
});

async function confirmMatch(comicvineId, uploadedPath) {
  candidateList.innerHTML = "<p>Saving…</p>";
  await fetch(`${API}/comics`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ comicvine_id: comicvineId, uploaded_image_path: uploadedPath }),
  });
  modal.classList.add("hidden");
  await Promise.all([loadComics(), loadCharacters(), loadFilterOptions()]);
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str || "";
  return div.innerHTML;
}

// ---------- init ----------
loadComics();
loadCharacters();
loadFilterOptions();
