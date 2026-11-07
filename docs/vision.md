# Image recognition

The detector is local OpenCV and NumPy. It does not call an external model.

## Steps

1. Load the screenshot with OpenCV, falling back to Pillow for formats OpenCV cannot decode.
2. Treat light, low-saturation pixels as gaps or page background. Colored cells and dark marks stay in the foreground.
3. Find external contours, keep blobs that are roughly square and similar in area, and ignore wide chrome such as a header bar.
4. Cluster blob centers into rows and columns. The gap threshold is a fraction of the median cell size, so the same code works for different resolutions.
5. If that grid covers at least 90% of its cells, crop to the blobs and continue. Otherwise perspective-correct the largest board-shaped region and try again.
6. Sample each cell from chromatic pixels only. Rounded corners, white gaps, black X marks, and cat icons are left out of the color median.
7. Cluster those Lab colors with a distance threshold. The cluster ids are labels, not fixed RGB values.
8. Name each cluster from its HSV hue, with separate handling for brown, gray, black, and white.
9. Score an X when dark pixels lie on both diagonals and the rest of the cell stays light. Score a cat when a compact dark blob fills the off-diagonal area.

## Confidence

Each cell stores a confidence value. The board needs review when confidence is low, any cell is missing, or the grid is not square. Missing cells are returned with no color. The pipeline does not invent a color for them.

## Limits

Very pale colors can look like gaps. Heavy blur can hide a thin X. Boards larger than 16×16 are rejected by the solver even if the grid is detected. The correction screen is the recovery path for all of these cases.
