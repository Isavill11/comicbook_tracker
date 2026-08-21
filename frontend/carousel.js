const slidesElement = document.getElementById("featuredSlides");
const progressElement = document.getElementById("carouselProgress");
const collectionRail = document.getElementById("collectionRail");
const previousButton = document.getElementById("carouselPrevious");
const nextButton = document.getElementById("carouselNext");

let comics = [];
let activeIndex = 0;
let rotationTimer;
let dragStartX = null;
const temporaryComic = {
  id: null,
  title: "Superboy-Prime",
  series: "Featured comic",
  issue_number: "",
  author: "Williamson, Mora, Sanchez",
  cover_date: "",
  storyline: "Superboy-Prime takes center stage in this featured issue from your collection.",
  cover_image_url: "/comics_db/superboy_prime.png",
};

function createTextElement(tagName, className, text) {
  const element = document.createElement(tagName);
  element.className = className;
  element.textContent = text;
  return element;
}

function renderCarousel() {
  slidesElement.innerHTML = "";
  progressElement.innerHTML = "";

  if (!comics.length) {
    slidesElement.appendChild(
      createTextElement("p", "featured-carousel__status", "Add a comic to see it featured here.")
    );
    previousButton.disabled = true;
    nextButton.disabled = true;
    return;
  }

  comics.forEach((comic, index) => {
    const slide = document.createElement("article");
    slide.className = "masthead-slide";
    slide.setAttribute("aria-roledescription", "slide");
    slide.setAttribute("aria-label", `${index + 1} of ${comics.length}`);

    const image = document.createElement("img");
    image.className = "masthead-slide__image";
    image.src = comic.cover_image_url || temporaryComic.cover_image_url;
    image.alt = `${comic.title || "Comic"} cover`;

    const content = document.createElement("div");
    content.className = "masthead-slide__content";
    content.appendChild(createTextElement("p", "masthead-slide__series", comic.series || "Featured from your library"));
    content.appendChild(createTextElement("h2", "masthead-slide__title", `${comic.title || "Untitled comic"}${comic.issue_number ? ` #${comic.issue_number}` : ""}`));
    content.appendChild(createTextElement("p", "masthead-slide__description", comic.storyline || "A new addition to your comic collection."));
    content.appendChild(createTextElement("p", "masthead-slide__meta", [comic.author, comic.cover_date].filter(Boolean).join("  |  ") || "Details coming soon"));
    const readLink = document.createElement("a");
    readLink.className = "masthead-slide__cta";
    readLink.href = comic.id ? `/comics/${comic.id}` : "/browse/comics";
    readLink.textContent = "Read";
    content.appendChild(readLink);

    slide.append(image, content);
    slidesElement.appendChild(slide);

    const progressButton = document.createElement("button");
    progressButton.className = "carousel-progress__dot";
    progressButton.type = "button";
    progressButton.setAttribute("aria-label", `Show ${comic.title || "comic"}`);
    progressButton.addEventListener("click", () => showSlide(index));
    progressElement.appendChild(progressButton);
  });

  previousButton.disabled = comics.length < 2;
  nextButton.disabled = comics.length < 2;
  showSlide(activeIndex);
}

function showSlide(index) {
  activeIndex = (index + comics.length) % comics.length;
  document.querySelectorAll(".masthead-slide").forEach((slide, slideIndex) => {
    const isActive = slideIndex === activeIndex;
    slide.classList.toggle("is-active", isActive);
    slide.setAttribute("aria-hidden", String(!isActive));
  });
  document.querySelectorAll(".carousel-progress__dot").forEach((dot, dotIndex) => {
    dot.classList.toggle("is-active", dotIndex === activeIndex);
    dot.setAttribute("aria-current", dotIndex === activeIndex ? "true" : "false");
  });
  restartRotation();
}

function renderCollectionRail() {
  collectionRail.innerHTML = "";
  if (!comics.length) {
    collectionRail.appendChild(
      createTextElement("p", "featured-carousel__status", "Add a comic to build your collection rail.")
    );
    return;
  }

  comics.forEach((comic) => {
    const card = document.createElement("a");
    card.className = "collection-card";
    card.href = comic.id ? `/comics/${comic.id}` : "/browse/comics";
    card.title = comic.title || "Comic";

    const image = document.createElement("img");
    image.src = comic.cover_image_url || temporaryComic.cover_image_url;
    image.alt = `${comic.title || "Comic"} cover`;
    card.appendChild(image);
    card.appendChild(createTextElement("span", "collection-card__title", `${comic.title || "Untitled"}${comic.issue_number ? ` #${comic.issue_number}` : ""}`));
    collectionRail.appendChild(card);
  });
}

function restartRotation() {
  window.clearInterval(rotationTimer);
  if (comics.length > 1) {
    rotationTimer = window.setInterval(() => showSlide(activeIndex + 1), 6500);
  }
}

async function loadFeaturedComics() {
  try {
    const response = await fetch("/api/comics");
    if (!response.ok) throw new Error("Unable to load comics");
    comics = [temporaryComic, ...(await response.json()).slice(0, 7)];
    renderCarousel();
    renderCollectionRail();
  } catch (error) {
    comics = [temporaryComic];
    renderCarousel();
    renderCollectionRail();
  }
}

function handleDragStart(event) {
  if (event.pointerType === "mouse" && event.button !== 0) return;
  dragStartX = event.clientX;
  slidesElement.setPointerCapture?.(event.pointerId);
}

function handleDragEnd(event) {
  if (dragStartX === null) return;
  const distance = event.clientX - dragStartX;
  dragStartX = null;
  if (Math.abs(distance) < 50 || comics.length < 2) return;
  showSlide(activeIndex + (distance < 0 ? 1 : -1));
}

slidesElement.addEventListener("pointerdown", handleDragStart);
slidesElement.addEventListener("pointerup", handleDragEnd);
slidesElement.addEventListener("pointercancel", () => {
  dragStartX = null;
});

previousButton.addEventListener("click", () => showSlide(activeIndex - 1));
nextButton.addEventListener("click", () => showSlide(activeIndex + 1));
loadFeaturedComics();