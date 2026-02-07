# Smart River Label Placement System

HackArena 3.0 – Problem 1  
Automatic and intelligent placement of river names inside complex river geometries.

---

## 📌 Overview

This project implements a robust geometric algorithm to place river labels inside irregular river polygons while ensuring:

- Proper boundary padding  
- High readability  
- Flow-aligned orientation  
- Visual consistency  

Unlike centroid-based methods, this system analyzes river geometry and identifies the most suitable placement zone.

---

## 🚀 Features

- Robust WKT file parsing
- Automatic MultiPolygon handling
- Safe-zone buffering (boundary protection)
- Oriented skeleton extraction
- Clearance-based optimization
- Flow-aligned text rotation
- Fallback placement mechanism
- High-quality visualization

---

## 🧠 Approach

The system follows a multi-stage geometric pipeline:

1. Parse river geometry from WKT
2. Extract the main river polygon
3. Apply negative buffer to create safe zone
4. Compute oriented centerline using scan lines
5. Sample candidate positions
6. Score candidates based on:
   - Boundary clearance
   - Local straightness
   - Centrality
7. Select best placement
8. Rotate label along river flow
9. Render final output

---

## 📂 Repository Structure

