# R: Strömungslinien mit aRtsy
# aRtsy (https://koenderks.github.io/aRtsy/) ist ein R-Paket für generative Kunst. Seine Bilder sind
# ggplot-Grafiken – plotart zeichnet sie automatisch. Einmalig installieren: install.packages("aRtsy")
library(aRtsy)
linien <- plotart_param("Linien", 800L, 100L, 3000L)
palette <- plotart_param("Palette", "blossom", options = c("blossom", "dark1", "neon1", "sooph", "tuscany3"))
polar <- plotart_param("Polar", FALSE)

plotart_canvas(800, 800)
canvas_flow(colors = colorPalette(palette), lines = linien, lwd = 0.5, polar = polar)
