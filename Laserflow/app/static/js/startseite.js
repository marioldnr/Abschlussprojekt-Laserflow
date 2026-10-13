/*
 * LaserFlow – startseite.js (nur für index.html)
 *
 * Bild im "Über uns"-Bereich leicht mit der Maus kippen.
 */

const tiltImage = document.getElementById("tilt-image");

tiltImage.addEventListener("mousemove", (event) => {
  const box = tiltImage.getBoundingClientRect();
  const x = (event.clientX - box.left) / box.width - 0.5;  // -0.5 bis 0.5
  const y = (event.clientY - box.top) / box.height - 0.5;
  tiltImage.style.transform = `perspective(900px) rotateY(${x * 8}deg) rotateX(${-y * 8}deg)`;
});

tiltImage.addEventListener("mouseleave", () => {
  tiltImage.style.transform = "";
});
