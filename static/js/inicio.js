
    async function actualizarTotales() {
      const res = await fetch('/api/dashboard_data');
      const data = await res.json();
      document.getElementById('total-administradores').innerText = data.total_administradores;
      document.getElementById('total-lectores').innerText = data.total_lectores;
      document.getElementById('total-libros').innerText = data.total_libros;
      document.getElementById('total-prestamos').innerText = data.total_prestamos;
      document.getElementById('total-reservas').innerText = data.total_reservas;
      document.getElementById('total-reportes').innerText = data.total_reportes;
    }

    actualizarTotales();
    setInterval(actualizarTotales, 30000);

    document.addEventListener("DOMContentLoaded", () => {

  // Gráfico: Libros más prestados
  fetch('/api/libros_populares')
    .then(res => res.json())
    .then(data => {
      const ctx = document.getElementById('graficoLibrosPopulares').getContext('2d');
      new Chart(ctx, {
        type: 'bar',
        data: {
          labels: data.map(d => d.titulo),
          datasets: [{
            label: 'Veces prestado',
            data: data.map(d => d.total),
            backgroundColor: '#1cc88a'
          }]
        },
        options: {
          responsive: true,
          plugins: {
            legend: { display: false }
          }
        }
      });
    });

  // Gráfico: Libros con más retraso
  fetch('/api/libros_atrasados')
    .then(res => res.json())
    .then(data => {
      const ctx = document.getElementById('graficoLibrosAtrasados').getContext('2d');
      new Chart(ctx, {
        type: 'bar',
        data: {
          labels: data.map(d => d.titulo),
          datasets: [{
            label: 'Veces atrasado',
            data: data.map(d => d.total),
            backgroundColor: '#e74a3b'
          }]
        },
        options: {
          responsive: true,
          plugins: {
            legend: { display: false }
          }
        }
      });
    });

});
