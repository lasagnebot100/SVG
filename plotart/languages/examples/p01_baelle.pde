// Processing: Bälle mit PVector und ArrayList
// Ein typischer Processing-Sketch mit einer Klasse. ▶ Ausführen startet ihn mit Processing,
// ⇄ nach plotart überträgt ihn nach plotart-Python. Mausklick: anhalten / weiter.
ArrayList<Ball> balls = new ArrayList<Ball>();
int count = 30;
boolean paused = false;

void setup() {
  size(600, 400);
  for (int i = 0; i < count; i++) {
    balls.add(new Ball(random(width), random(height), random(8, 24)));
  }
}

void draw() {
  if (paused) return;
  background(16, 16, 32);
  for (Ball b : balls) {
    b.update();
    b.show();
  }
  fill(255);
  text("Bälle: " + balls.size() + " · Bild " + frameCount, 10, 20);
}

void mousePressed() {
  paused = !paused;
}

class Ball {
  PVector pos, vel;
  float r;

  Ball(float x, float y, float r_) {
    pos = new PVector(x, y);
    vel = PVector.random2D();
    vel.mult(random(1, 3));
    r = r_;
  }

  void update() {
    pos.add(vel);
    if (pos.x < r || pos.x > width - r) vel.x *= -1;
    if (pos.y < r || pos.y > height - r) {
      vel.y = -vel.y;
    }
  }

  void show() {
    noStroke();
    fill(map(pos.x, 0, width, 100, 255), 120, 200, 180);
    ellipse(pos.x, pos.y, r * 2, r * 2);
  }
}
