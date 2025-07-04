document.addEventListener("DOMContentLoaded", function () {
  const modal = new bootstrap.Modal(document.getElementById("modalReporte"));
  const modalBody = document.getElementById("modal-reporte-body");

  const cargarReporte = (url) => {
    fetch(url)
      .then(response => response.text())
      .then(html => {
        modalBody.innerHTML = html;
        modal.show();
      })
      .catch(error => {
        modalBody.innerHTML = `<div class="text-danger">Error al cargar el reporte.</div>`;
      });
  };

  document.getElementById("btn-libros-atrasados")?.addEventListener("click", () => {
    cargarReporte("/admin/reportes/atrasados");
  });

  document.getElementById("btn-libros-prestados")?.addEventListener("click", () => {
    cargarReporte("/admin/reportes/prestados");
  });

  document.getElementById("btn-libros-populares")?.addEventListener("click", () => {
    cargarReporte("/admin/reportes/populares");
  });
});
