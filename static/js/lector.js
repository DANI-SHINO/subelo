let index = 0;

function moveSlide(step) {
  const slideContainer = document.querySelector('.carousel-slide');
  const images = slideContainer.querySelectorAll('img');
  const total = images.length;

  index = (index + step + total) % total;
  slideContainer.style.transform = `translateX(-${index * 100}%)`;

  img.addEventListener('click', () => {
  const src = img.getAttribute('src');
  console.log("Hiciste clic en:", src); // ✅ esto te dice si la imagen se está capturando bien

  localStorage.setItem("favoriteBooks", JSON.stringify(favorites));

  
  
});
}
