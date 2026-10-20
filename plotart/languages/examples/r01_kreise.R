# R: Kreise mit Basisgrafik
# Ein R-Skript läuft mit deinem installierten R (Rscript). plotart_param() erzeugt Regler,
# plotart_canvas() legt die Bildgröße fest, der Seed gilt für runif(), rnorm() und Co.
anzahl <- plotart_param("Anzahl", 60L, 5L, 400L)
farbe <- plotart_param("Farbe", "#1f5fbf")
groesse <- plotart_param("Größe", 0.08, 0.01, 0.3)

plotart_canvas(800, 800)
par(mar = c(0, 0, 0, 0), bg = "#f6f3ec")
plot.new()
plot.window(c(0, 1), c(0, 1), asp = 1)
x <- runif(anzahl)
y <- runif(anzahl)
r <- runif(anzahl) * groesse
symbols(x, y, circles = r, inches = FALSE, add = TRUE, fg = farbe, lwd = 2)
cat("Kreise:", anzahl, "\n")
