function updateCopyrightYearRange() {
  const startYear = 2025;
  const currentYear = new Date().getFullYear();
  const yearRange = currentYear > startYear ? `${startYear}-${currentYear}` : `${startYear}`;
  const node = document.getElementById("copyright-year-range");
  if (node) {
    node.textContent = yearRange;
  }
}

if (typeof document$ !== "undefined") {
  document$.subscribe(updateCopyrightYearRange);
} else if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", updateCopyrightYearRange);
} else {
  updateCopyrightYearRange();
}
