"""
FINAL SUBMISSION VERSION – NORMALIZED
HackArena 3.0 – Smart River Label Placement
Handles Lat/Lon + Meter Coordinates
"""

import os
import math
import re
import numpy as np
import matplotlib.pyplot as plt

from shapely import wkt
from shapely.geometry import Polygon, MultiPolygon, LineString, Point
from shapely.affinity import scale, translate


# ==================================================
# CONFIG
# ==================================================

DEFAULT_FILE = "Problem 1 - river.wkt"
DEFAULT_LABEL = "ELBE"
DEFAULT_FONT = 12
DEFAULT_PADDING = 4.0

TARGET_SIZE = 1000.0   # normalize to 1000x1000


# ==================================================
# NORMALIZER
# ==================================================

class GeometryNormalizer:

    def __init__(self, geom):

        minx, miny, maxx, maxy = geom.bounds

        self.minx = minx
        self.miny = miny

        width = maxx - minx
        height = maxy - miny

        self.scale_factor = TARGET_SIZE / max(width, height)


    def normalize(self, geom):

        g = translate(geom, xoff=-self.minx, yoff=-self.miny)

        g = scale(
            g,
            xfact=self.scale_factor,
            yfact=self.scale_factor,
            origin=(0, 0)
        )

        return g


    def denormalize_point(self, x, y):

        x = x / self.scale_factor + self.minx
        y = y / self.scale_factor + self.miny

        return x, y


# ==================================================
# GEOMETRY ENGINE
# ==================================================

class RiverGeometryEngine:

    def __init__(self, filename):

        self.filename = filename

        self.original_geom = self._load_wkt()
        self.normalizer = GeometryNormalizer(self.original_geom)

        self.geom = self.normalizer.normalize(self.original_geom)


    def _load_wkt(self):

        with open(self.filename, "r", encoding="utf-8-sig") as f:
            raw = f.read()

        raw = raw.replace("\ufeff", "").strip()

        blocks = re.split(r"\s*POLYGON", raw)

        polys = []

        for b in blocks:

            if not b.strip():
                continue

            try:
                if not b.startswith("(("):
                    b = "((" + b

                if not b.endswith("))"):
                    b = b.rstrip(")") + "))"

                s = "POLYGON" + b

                g = wkt.loads(s)

                if not g.is_valid:
                    g = g.buffer(0)

                polys.append(g)

            except:
                continue

        if not polys:
            raise ValueError("Invalid WKT geometry")

        return max(polys, key=lambda p: p.area)



# ==================================================
# LABEL ENGINE
# ==================================================

class RiverLabelEngine:

    def __init__(self, river, font, padding):

        self.river = river
        self.font = font
        self.padding = padding

        self.safe = self._safe_zone()


    def _safe_zone(self):

        buf = self.river.buffer(-self.padding)

        if buf.is_empty:
            return self.river

        if isinstance(buf, MultiPolygon):
            return max(buf.geoms, key=lambda g: g.area)

        return buf


    def _centerline(self, scans=250):

        poly = self.safe

        rect = poly.minimum_rotated_rectangle
        pts = np.array(rect.exterior.coords)

        edges = np.linalg.norm(pts[1:] - pts[:-1], axis=1)

        i = np.argmax(edges)

        main = pts[i+1] - pts[i]
        main = main / np.linalg.norm(main)

        perp = np.array([-main[1], main[0]])

        origin = np.array(rect.centroid.coords[0])

        proj = np.dot(np.array(poly.exterior.coords), main)

        pmin, pmax = proj.min(), proj.max()

        scan = np.linspace(pmin, pmax, scans)

        L = max(poly.bounds) * 3

        mids = []

        for s in scan:

            base = origin + (s - np.dot(origin, main)) * main

            a = base - perp * L
            b = base + perp * L

            line = LineString([a, b])

            inter = poly.intersection(line)

            if inter.is_empty:
                continue

            if inter.geom_type == "LineString":
                mids.append(inter.interpolate(0.5, True))

            elif inter.geom_type == "MultiLineString":

                seg = max(inter.geoms, key=lambda g: g.length)
                mids.append(seg.interpolate(0.5, True))

        if len(mids) < 10:
            return None

        return LineString(mids)


    def find(self, text):

        spine = self._centerline()

        if spine is None:
            return None, None, None


        pts = np.array(spine.coords)

        best = None
        best_score = -1


        for i, p in enumerate(pts):

            point = Point(p)

            if not self.safe.contains(point):
                continue

            clear = point.distance(self.river.boundary)

            if clear < self.font:
                continue


            straight = self._straight(pts, i)

            score = clear * 0.7 + straight * 0.3

            if score > best_score:
                best_score = score
                best = p


        if best is None:
            return None, None, None


        ang = self._angle(pts, best)

        return best[0], best[1], ang


    def _straight(self, pts, i, w=6):

        a = max(0, i-w)
        b = min(len(pts), i+w)

        seg = pts[a:b]

        if len(seg) < 3:
            return 0.5

        return 1.0 / (1 + np.var(seg[:,0]) + np.var(seg[:,1]))


    def _angle(self, pts, p):

        d = np.linalg.norm(pts - p, axis=1)

        near = pts[d < self.font*4]

        if len(near) < 2:
            return 0

        dx = near[-1,0] - near[0,0]
        dy = near[-1,1] - near[0,1]

        a = math.degrees(math.atan2(dy, dx))

        if a > 90: a -= 180
        if a < -90: a += 180

        return a



# ==================================================
# VISUAL
# ==================================================

def plot(orig, x, y, angle, text, font):

    fig, ax = plt.subplots(figsize=(12,14))

    if isinstance(orig, MultiPolygon):

        for g in orig.geoms:
            X,Y = g.exterior.xy
            ax.fill(X,Y, "#7EC8E3")

    else:
        X,Y = orig.exterior.xy
        ax.fill(X,Y, "#7EC8E3")


    ax.text(
        x, y, text,
        fontsize=font*1.4,
        rotation=angle,
        ha="center",
        va="center",
        weight="bold",
        color="darkred"
    )


    ax.set_aspect("equal")
    ax.set_title("Smart River Label Placement")
    ax.axis("off")

    plt.show()



# ==================================================
# MAIN
# ==================================================

def main():

    print("\nSMART RIVER LABEL PLACEMENT (AUTO-SCALED)\n")


    f = input(f"File [{DEFAULT_FILE}]: ").strip() or DEFAULT_FILE
    t = input(f"Label [{DEFAULT_LABEL}]: ").strip() or DEFAULT_LABEL
    fs = float(input(f"Font [{DEFAULT_FONT}]: ") or DEFAULT_FONT)
    pd = float(input(f"Padding [{DEFAULT_PADDING}]: ") or DEFAULT_PADDING)


    print("\nLoading geometry...")

    eng = RiverGeometryEngine(f)


    print("Optimizing...")

    placer = RiverLabelEngine(eng.geom, fs, pd)

    x,y,a = placer.find(t)


    if x is None:

        c = eng.geom.centroid
        x,y = c.x, c.y
        a = 0


    # Map back
    rx, ry = eng.normalizer.denormalize_point(x, y)


    print("\nResult:")
    print("Position:", rx, ry)
    print("Angle:", a)


    plot(eng.original_geom, rx, ry, a, t, fs)


    print("\nDone.")



# ==================================================
# RUN
# ==================================================

if __name__ == "__main__":
    main()
