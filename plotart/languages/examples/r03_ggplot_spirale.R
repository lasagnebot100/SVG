# R: Phyllotaxis-Spirale mit ggplot2
# Der goldene Winkel (137,5°) verteilt Punkte wie Kerne in einer Sonnenblume.
# Einmalig installieren: install.packages("ggplot2")
library(ggplot2)
punkte <- plotart_param("Punkte", 1500L, 100L, 6000L)
winkel <- plotart_param("Winkel (Grad)", 137.508, 130, 145)
groesse <- plotart_param("Punktgröße", 2.5, 0.5, 8)

i <- seq_len(punkte)
df <- data.frame(
  x = sqrt(i) * cos(i * winkel * pi / 180),
  y = sqrt(i) * sin(i * winkel * pi / 180),
  t = i / punkte
)
plotart_canvas(800, 800)
ggplot(df, aes(x, y, colour = t, size = t)) +
  geom_point(alpha = 0.85) +
  scale_colour_gradientn(colours = c("#2c2f5b", "#5b6ee1", "#f2c14e", "#f25f5c")) +
  scale_size(range = c(groesse * 0.3, groesse)) +
  coord_equal() +
  theme_void() +
  theme(legend.position = "none", plot.background = element_rect(fill = "#0f1020", colour = NA))
