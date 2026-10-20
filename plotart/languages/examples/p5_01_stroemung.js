// p5.js: Teilchen im Strömungsfeld
// Ein p5.js-Sketch läuft direkt im Browser. plotart.param() erzeugt Regler im Studio – weil sie in
// draw() abgefragt werden, wirken sie sofort, ohne Neustart. Der Seed bestimmt random() und noise().
let teilchen = [];

function setup() {
  createCanvas(700, 700);
  background(12, 14, 30);
  for (let i = 0; i < 1500; i++) teilchen.push(createVector(random(width), random(height)));
}

function draw() {
  const zoom = plotart.param("Noise-Zoom", 0.004, 0.001, 0.02);
  const tempo = plotart.param("Tempo", 1.5, 0.2, 5.0);
  const spur = plotart.param("Spuren", 12, 0, 60);
  noStroke();
  fill(12, 14, 30, spur);
  rect(0, 0, width, height);
  stroke(242, 193, 78, 120);
  for (const p of teilchen) {
    const a = noise(p.x * zoom, p.y * zoom, frameCount * 0.003) * TWO_PI * 2;
    const q = p.copy();
    p.add(cos(a) * tempo, sin(a) * tempo);
    if (p.x < 0 || p.x > width || p.y < 0 || p.y > height) p.set(random(width), random(height));
    else line(q.x, q.y, p.x, p.y);
  }
}
