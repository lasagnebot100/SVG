// p5.js: Truchet-Kacheln
// Ein statischer Sketch (noLoop): Die Regler werden in setup() gelesen, deshalb startet der
// Sketch bei jeder Änderung neu. Mit ◀ ▶ neben dem Seed durch die Varianten blättern.
function setup() {
  const raster = plotart.param("Raster", 12, 3, 40);
  const dicke = plotart.param("Strichstärke", 6, 1, 20);
  const farbe = plotart.param("Farbe", "#1f5fbf");
  createCanvas(600, 600);
  background(246, 243, 236);
  noFill();
  stroke(farbe);
  strokeWeight(dicke);
  strokeCap(SQUARE);
  const s = width / raster;
  for (let y = 0; y < raster; y++) {
    for (let x = 0; x < raster; x++) {
      push();
      translate(x * s + s / 2, y * s + s / 2);
      rotate(HALF_PI * floor(random(4)));
      arc(-s / 2, -s / 2, s, s, 0, HALF_PI);
      arc(s / 2, s / 2, s, s, PI, PI + HALF_PI);
      pop();
    }
  }
  noLoop();
}
