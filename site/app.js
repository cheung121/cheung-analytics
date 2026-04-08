async function loadLatestDraft() {
  const title = document.querySelector("#latest-title");
  const summary = document.querySelector("#latest-summary");
  const graphic = document.querySelector("#latest-graphic");
  const link = document.querySelector("#latest-link");

  try {
    const response = await fetch("generated/index.json", { cache: "no-store" });
    if (!response.ok) {
      throw new Error(`Latest draft metadata returned ${response.status}`);
    }

    const data = await response.json();
    const latest = data.latest;
    if (!latest) {
      return;
    }

    title.textContent = latest.title;
    summary.textContent = latest.summary;
    graphic.src = latest.graphic;
    graphic.alt = latest.alt;
    link.href = latest.post_json;
    link.textContent = "View generated draft";
  } catch (error) {
    console.info("Using default latest-card placeholder:", error.message);
  }
}

loadLatestDraft();

