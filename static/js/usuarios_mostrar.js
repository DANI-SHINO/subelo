document.addEventListener("DOMContentLoaded", () => {
  const tabla = document.getElementById("tabla-usuarios");
  const contenedorFormulario = document.getElementById("contenedor-formulario-usuario");

  tabla.addEventListener("click", (event) => {
    const target = event.target;

    // Botón editar
    if (target.closest(".btn-editar-usuario")) {
      const btn = target.closest(".btn-editar-usuario");
      const userId = btn.getAttribute("data-id");
      console.log(`Editar usuario ID: ${userId}`);

      // ✅ Traer el formulario vía GET correcto
      fetch(`/admin/usuarios/editar_formulario/${userId}`)
        .then(res => res.text())
        .then(html => {
          contenedorFormulario.innerHTML = html;
          window.scrollTo({ top: contenedorFormulario.offsetTop, behavior: "smooth" });
        })
        .catch(err => {
          console.error("Error cargando formulario:", err);
        });
    }

    // Botón eliminar
    if (target.closest(".btn-eliminar-usuario")) {
      const btn = target.closest(".btn-eliminar-usuario");
      const userId = btn.getAttribute("data-id");
      if (confirm("¿Estás seguro de eliminar este usuario?")) {
        fetch(`/admin/usuarios/eliminar/${userId}`, { method: "POST" })
          .then(res => res.json())
          .then(data => {
            if (data.success) {
              alert("Usuario eliminado");
              location.reload();
            } else {
              alert("Error al eliminar");
            }
          });
      }
    }
  });

  const inputBusqueda = document.getElementById("busqueda-usuario");
  inputBusqueda.addEventListener("keyup", () => {
    const filtro = inputBusqueda.value.toLowerCase();
    document.querySelectorAll("#tabla-usuarios tbody tr").forEach((fila) => {
      const texto = fila.textContent.toLowerCase();
      fila.style.display = texto.includes(filtro) ? "" : "none";
    });
  });
});
