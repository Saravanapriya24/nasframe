document.addEventListener("click", function (e) {
  const btn = e.target.closest(".img-btn");
  if (!btn) return;
  document.getElementById("imageModalImg").src = btn.dataset.full;
  document.getElementById("imageModalImg").alt = btn.dataset.title;
  document.getElementById("imageModalTitle").textContent = btn.dataset.title;
  new bootstrap.Modal(document.getElementById("imageModal")).show();
});