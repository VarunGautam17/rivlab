"""
FINAL SUBMISSION VERSION
HackArena 3.0 – Smart River Label Placement

Features:
✔ Robust WKT Parsing
✔ Safe-Zone Padding
✔ Oriented Skeletonization
✔ Width + Clearance Optimization
✔ Rotation Along Flow
✔ Fallback Handling
✔ Stable on Real Data
✔ Single-File Submission
"""

import os
import sys
import math
import re
import numpy as np
import matplotlib.pyplot as plt

from shapely import wkt
from shapely.geometry import (
    Polygon,
    MultiPolygon,
    LineString,
    Point
)
from shapely.ops import unary_union


# ==================================================
# CONFIG
# ==================================================

DEFAULT_FILE = "Problem 1 - river.wkt"
DEFAULT_LABEL = "ELBE"
DEFAULT_FONT = 12
DEFAULT_PADDING = 4.0


# ==================================================
# GEOMETRY ENGINE
# ==================================================

class RiverGeometryEngine:

    def __init__(self, filename):

        if not os.path.exists(filename):
            raise FileNotFoundError(f"{filename} not found")

        self.filename = filename
        self.polygons = self._load_wkt()
        self.river = self._get_main_polygon()


    # --------------------------
    # Robust WKT Loader
    # --------------------------

    def _load_wkt(self):

        with open(self.filename, "r", encoding="utf-8-sig") as f:
            text = f.read()

        text = text.replace("\ufeff", "").strip()

        parts = re.split(r"\s*POLYGON", text)
        parts = [p.strip() for p in parts if p.strip()]

        polygons = []

        for part in parts:

            try:
                if not part.startswith("(("):
                    part = "((" + part

                if not part.endswith("))"):
                    part = part.rstrip(")") + "))"

                wkt_str = "POLYGON" + part

                poly = wkt.loads(wkt_str)

                if not poly.is_valid:
                    poly = poly.buffer(0)

                polygons.append(poly)

            except:
                continue

        if not polygons:
            raise ValueError("No valid polygons in WKT file")

        return polygons


    def _get_main_polygon(self):

        if len(self.polygons) == 1:
            return self.polygons[0]

        return max(self.polygons, key=lambda p: p.area)



# ==================================================
# LABEL ENGINE
# ==================================================

class RiverLabelEngine:

    def __init__(self, river_poly, font_size=12, padding=3):

        self.river = river_poly
        self.font = float(font_size)
        self.padding = float(padding)

        self.safe_zone = self._create_safe_zone()


    # --------------------------
    # Padding Zone
    # --------------------------

    def _create_safe_zone(self):

        safe = self.river.buffer(-self.padding)

        if safe.is_empty:

            print("⚠ Padding too large. Using original geometry.")
            return self.river

        if isinstance(safe, MultiPolygon):
            return max(safe.geoms, key=lambda g: g.area)

        return safe


    # --------------------------
    # Oriented Skeleton
    # --------------------------

    def _extract_centerline(self, scans=200):

        poly = self.safe_zone

        rect = poly.minimum_rotated_rectangle
        coords = np.array(rect.exterior.coords)

        edges = np.linalg.norm(coords[1:] - coords[:-1], axis=1)
        idx = np.argmax(edges)

        main_vec = coords[idx+1] - coords[idx]
        main_len = np.linalg.norm(main_vec)

        if main_len == 0:
            return None

        main_dir = main_vec / main_len
        perp = np.array([-main_dir[1], main_dir[0]])

        origin = np.array(rect.centroid.coords[0])
        proj0 = np.dot(origin, main_dir)

        pts = np.array(poly.exterior.coords)
        proj = np.dot(pts, main_dir)

        pmin, pmax = proj.min(), proj.max()

        scan_pos = np.linspace(pmin, pmax, scans)

        scan_len = max(self.river.bounds) * 5

        centers = []

        for s in scan_pos:

            base = origin + (s - proj0) * main_dir

            p1 = base - perp * scan_len
            p2 = base + perp * scan_len

            scan = LineString([p1, p2])

            inter = poly.intersection(scan)

            if inter.is_empty:
                continue

            if inter.geom_type == "LineString":

                centers.append(
                    inter.interpolate(0.5, normalized=True)
                )

            elif inter.geom_type == "MultiLineString":

                seg = max(inter.geoms, key=lambda g: g.length)

                centers.append(
                    seg.interpolate(0.5, normalized=True)
                )

        if len(centers) < 5:
            return None

        return LineString(centers)


    # --------------------------
    # Placement Optimization
    # --------------------------

    def find_best_position(self, text):

        centerline = self._extract_centerline()

        if centerline is None:
            return None, None, None


        coords = np.array(centerline.coords)

        dists = [0]

        for i in range(1, len(coords)):
            d = np.linalg.norm(coords[i] - coords[i-1])
            dists.append(dists[-1] + d)

        total_len = dists[-1]


        char_w = self.font * 0.6
        text_len = len(text) * char_w


        best = None
        best_score = -1


        for i in range(len(coords)):

            pos = coords[i]

            point = Point(pos)

            if not self.safe_zone.contains(point):
                continue


            clearance = point.distance(self.river.boundary)

            if clearance < self.font:
                continue


            straight = self._straightness(coords, i)

            central = 1.0 / (1.0 + point.distance(self.river.centroid))


            score = (
                clearance * 0.5 +
                straight * 0.3 +
                central * 0.2
            )

            if score > best_score:

                best_score = score
                best = pos


        if best is None:
            return None, None, None


        angle = self._flow_angle(coords, best)


        return best[0], best[1], angle


    # --------------------------
    # Helpers
    # --------------------------

    def _straightness(self, pts, i, win=6):

        start = max(0, i-win)
        end = min(len(pts), i+win)

        seg = pts[start:end]

        if len(seg) < 3:
            return 0.5

        x = seg[:, 0]
        y = seg[:, 1]

        return 1.0 / (1.0 + np.var(x) + np.var(y))


    def _flow_angle(self, pts, pos, radius=5):

        dists = np.linalg.norm(pts - pos, axis=1)

        mask = dists < radius * self.font

        nearby = pts[mask]

        if len(nearby) < 2:
            return 0


        dx = nearby[-1,0] - nearby[0,0]
        dy = nearby[-1,1] - nearby[0,1]

        ang = math.degrees(math.atan2(dy, dx))

        if ang > 90:
            ang -= 180
        if ang < -90:
            ang += 180

        return ang



# ==================================================
# VISUALIZATION
# ==================================================

def visualize(river, pos, angle, text, font):

    fig, ax = plt.subplots(figsize=(12, 14))

    if isinstance(river, MultiPolygon):

        for g in river.geoms:
            x,y = g.exterior.xy
            ax.fill(x,y, color="#7EC8E3", alpha=0.8)

    else:
        x,y = river.exterior.xy
        ax.fill(x,y, color="#7EC8E3", alpha=0.8)


    ax.text(
        pos[0], pos[1],
        text,
        fontsize=font * 1.4,
        fontweight="bold",
        ha="center",
        va="center",
        rotation=angle,
        color="darkred",
        zorder=10
    )


    ax.set_aspect("equal")
    ax.set_title("Smart River Label Placement", fontsize=18)
    ax.axis("off")

    plt.tight_layout()
    plt.show()



# ==================================================
# MAIN
# ==================================================

def main():

    print("\n" + "="*60)
    print("SMART RIVER LABEL PLACEMENT – FINAL VERSION")
    print("="*60 + "\n")


    fname = input(f"File [{DEFAULT_FILE}]: ").strip()
    fname = fname if fname else DEFAULT_FILE

    label = input(f"Label [{DEFAULT_LABEL}]: ").strip()
    label = label if label else DEFAULT_LABEL

    size = input(f"Font [{DEFAULT_FONT}]: ").strip()
    size = float(size) if size else DEFAULT_FONT

    pad = input(f"Padding [{DEFAULT_PADDING}]: ").strip()
    pad = float(pad) if pad else DEFAULT_PADDING


    print("\nLoading geometry...")

    engine = RiverGeometryEngine(fname)

    print("✓ Geometry loaded")


    print("Optimizing placement...")

    placer = RiverLabelEngine(
        engine.river,
        size,
        pad
    )


    x,y,angle = placer.find_best_position(label)


    if x is None:

        print("⚠ No valid position found. Using centroid.")

        c = engine.river.centroid

        x,y = c.x, c.y
        angle = 0


    print("\nRESULT")
    print(f"Position : ({x:.2f}, {y:.2f})")
    print(f"Rotation : {angle:.2f}°")


    visualize(engine.river, (x,y), angle, label, size)


    print("\n✓ Done.")



# ==================================================
# RUN
# ==================================================

if __name__ == "__main__":
    main()
