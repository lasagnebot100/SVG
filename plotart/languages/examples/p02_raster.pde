// Processing: Statisches Raster
// Ein Sketch ohne setup() und draw() (statischer Modus). Ganzzahlen bleiben Ganzzahlen:
// k / 2 rechnet wie in Java ohne Nachkommastellen – die Übertragung macht daraus k // 2.
size(400, 400);
background(255);
noFill();
int n = 10;
float step = width / n;
for (int y = 0; y <= n; y += 2) {
  for (int x = n; x > 0; x--) {
    int k = (x + y) % 3;
    stroke(k == 0 ? color(220, 40, 60) : color(20));
    strokeWeight((float) k + 0.5);
    float d = step * (k / 2 + 1);
    rect(x * step, y * step, d, d);
  }
}
println("fertig: " + n * n + " Felder");
