document.addEventListener("DOMContentLoaded", function () {
  const modalElement = document.getElementById("modalLibro");
  const modalBody = document.getElementById("modal-libro-body");
  const modalTitle = document.getElementById("modalLibroLabel");
  const modalInstance = new bootstrap.Modal(modalElement);

  // Animación suave
  const aplicarAnimacion = (elemento) => {
    elemento.style.opacity = 0;
    elemento.style.transform = "translateY(40px)";
    elemento.style.transition = "opacity 0.2s ease, transform 0.2s ease";
    setTimeout(() => {
      elemento.style.opacity = 1;
      elemento.style.transform = "translateY(0)";
    }, 10);
  };

  // Spinner mientras carga
  const mostrarCargando = (contenedor) => {
    contenedor.innerHTML = `
      <div class="d-flex justify-content-center align-items-center p-4">
        <div class="spinner-border text-primary" role="status">
          <span class="visually-hidden">Cargando...</span>
        </div>
      </div>
    `;
  };

  // Mostrar lista de libros
  document.getElementById("btn-mostrar-libros")?.addEventListener("click", () => {
    modalTitle.textContent = "Lista de Libros";
    mostrarCargando(modalBody);

    fetch("/admin/libros/mostrar")
      .then(res => res.text())
      .then(html => {
        modalBody.innerHTML = html;
        aplicarAnimacion(modalBody);
        modalInstance.show();
        asignarEventosBotonesEditar();
      });
  });

  // Mostrar formulario para agregar libro
  document.getElementById("btn-agregar")?.addEventListener("click", () => {
    modalTitle.textContent = "Agregar Libro";
    mostrarCargando(modalBody);

    fetch("/admin/libros/nuevo")
      .then(res => res.text())
      .then(html => {
        modalBody.innerHTML = html;
        aplicarAnimacion(modalBody);
        modalInstance.show();
      });
  });

  // Delegación para editar libro desde tabla
  document.addEventListener("click", function (e) {
    if (e.target.classList.contains("btn-editar")) {
      const libroId = e.target.getAttribute("data-id");
      modalTitle.textContent = "Editar Libro";
      mostrarCargando(modalBody);

      fetch(`/admin/libros/editar/${libroId}`)
        .then(res => res.text())
        .then(html => {
          modalBody.innerHTML = html;
          aplicarAnimacion(modalBody);
          modalInstance.show();
        });
    }
  });

  // Filtro en tabla de libros (en caso de que esté cargada en el modal)
  document.addEventListener("keyup", function (e) {
    if (e.target.id === "busqueda-libro") {
      const filtro = e.target.value.toLowerCase();
      const filas = document.querySelectorAll("#tabla-libros tbody tr");

      filas.forEach(fila => {
        const titulo = fila.dataset.titulo;
        const autor = fila.dataset.autor;
        const isbn = fila.dataset.isbn;
        const categoria = fila.dataset.categoria;
        const coincide = titulo.includes(filtro) || autor.includes(filtro) || isbn.includes(filtro) || categoria.includes(filtro);
        fila.style.display = coincide ? "" : "none";
      });
    }
  });

  // Asignar eventos a botones "Editar" dentro del contenido cargado
  function asignarEventosBotonesEditar() {
    document.querySelectorAll(".btn-editar").forEach((btn) => {
      btn.addEventListener("click", function () {
        const libroId = this.getAttribute("data-id");
        modalTitle.textContent = "Editar Libro";
        mostrarCargando(modalBody);

        fetch(`/admin/libros/editar/${libroId}`)
          .then(res => res.text())
          .then(html => {
            modalBody.innerHTML = html;
            aplicarAnimacion(modalBody);
            modalInstance.show();
          });
      });
    });
  }
});
