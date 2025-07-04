
document.getElementById("form-prestamo").addEventListener("submit", function (e) {
  e.preventDefault();

  const datos = {
    usuario_id: document.getElementById("usuario_id").value,
    libro_id: document.getElementById("libro_id").value,
    fecha_prestamo: document.getElementById("fecha_prestamo").value
  };

  fetch("/admin/prestamos/guardar", {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(datos)
  })
    .then(res => res.json())
    .then(respuesta => {
      if (respuesta.mensaje) {
        document.getElementById("notificacion-prestamo").classList.remove("d-none");
        // Opcional: limpiar formulario
        document.getElementById("form-prestamo").reset();
      }
    });
});
