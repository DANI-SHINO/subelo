document.addEventListener("DOMContentLoaded", function () {
  const modalElement = document.getElementById("modalPrestamo");
  const modalBody = document.getElementById("modal-prestamo-body");
  const modalTitle = document.getElementById("modalPrestamoLabel");
  const contenido = document.getElementById("contenido-opcion");

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

  // Cargar contenido dinámico
  const cargarContenido = (url, forzarModal = false) => {
    const mostrarEnModal = url.includes("nuevo") || url.includes("editar") || forzarModal;

    if (mostrarEnModal) {
      modalTitle.textContent = url.includes("nuevo")
        ? "Agregar Préstamo"
        : url.includes("editar")
        ? "Editar Préstamo"
        : "Lista de Préstamos";

      mostrarCargando(modalBody);

      fetch(url)
        .then((response) => response.text())
        .then((html) => {
          modalBody.innerHTML = html;
          aplicarAnimacion(modalBody);
          new bootstrap.Modal(modalElement).show();

          if (url.includes("nuevo")) {
            setTimeout(inicializarFormularioPrestamo, 100);
          }
        });
    } else {
      mostrarCargando(contenido);
      fetch(url)
        .then((response) => response.text())
        .then((html) => {
          contenido.innerHTML = html;
          aplicarAnimacion(contenido);
        });
    }
  };

  // Eventos
  document.getElementById("btn-mostrar-prestamos")?.addEventListener("click", () => {
    cargarContenido("/admin/prestamos/mostrar", true);  // 🔁 forzar a que se cargue en modal
  });

  document.getElementById("btn-agregar-prestamos")?.addEventListener("click", () => {
    cargarContenido("/admin/prestamos/nuevo");
  });

  // Formulario de préstamo
  function inicializarFormularioPrestamo() {
    const form = document.getElementById("form-prestamo");
    if (!form) return;

    form.addEventListener("submit", function (e) {
      e.preventDefault();

      const datos = {
        usuario_id: document.getElementById("usuario_id").value,
        libro_id: document.getElementById("libro_id").value,
        fecha_prestamo: document.getElementById("fecha_prestamo").value
      };

      fetch("/admin/prestamos/guardar", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(datos)
      })
        .then((res) => res.json())
        .then((respuesta) => {
          if (respuesta.mensaje) {
            document.getElementById("notificacion-prestamo")?.classList.remove("d-none");
            form.reset();
          }
        })
        .catch((err) => {
          console.error("Error al guardar préstamo:", err);
          alert("Error al guardar el préstamo.");
        });
    });
  }
});
