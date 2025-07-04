let modo = null;
let usuarioSeleccionado = null;

document.addEventListener("DOMContentLoaded", () => {
  const editarBtn = document.getElementById("btn-editar");
  const eliminarBtn = document.getElementById("btn-eliminar");
  const tabla = document.getElementById("tabla-usuarios");

  if (editarBtn) {
    editarBtn.addEventListener("click", () => {
      modo = "editar";
      activarSeleccion();
    });
  }

  if (eliminarBtn) {
    eliminarBtn.addEventListener("click", () => {
      modo = "eliminar";
      activarSeleccion();
    });
  }

  function activarSeleccion() {
    document.querySelectorAll("#tabla-usuarios tbody tr").forEach(fila => {
      fila.addEventListener("click", () => {
        usuarioSeleccionado = {
          id: fila.dataset.id,
          nombre: fila.dataset.nombre,
          email: fila.dataset.email,
          rol: fila.dataset.rol
        };
        abrirModal(usuarioSeleccionado);
      });
    });
  }

  function abrirModal(usuario) {
    document.getElementById("usuario-id").value = usuario.id;
    document.getElementById("usuario-nombre").value = usuario.nombre;
    document.getElementById("usuario-email").value = usuario.email;
    document.getElementById("usuario-rol").value = usuario.rol;

    document.getElementById("btn-confirmar-eliminar").classList.toggle("d-none", modo !== "eliminar");
    document.getElementById("btn-guardar").classList.toggle("d-none", modo !== "editar");
    document.getElementById("alerta-eliminar").classList.toggle("d-none", modo !== "eliminar");

    new bootstrap.Modal(document.getElementById("modalUsuario")).show();
  }

  document.getElementById("formUsuario").addEventListener("submit", function (e) {
    e.preventDefault();
    if (modo === "editar") {
      const datos = {
        id: document.getElementById("usuario-id").value,
        nombre: document.getElementById("usuario-nombre").value,
        email: document.getElementById("usuario-email").value,
        rol: document.getElementById("usuario-rol").value
      };
      fetch("/admin/usuarios/editar", {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify(datos)
      }).then(() => location.reload());
    }
  });

  document.getElementById("btn-confirmar-eliminar").addEventListener("click", function () {
    fetch(`/admin/usuarios/eliminar/${usuarioSeleccionado.id}`, {
      method: "POST"
    }).then(() => location.reload());
  });
});
