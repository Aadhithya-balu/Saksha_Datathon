import os
import re
import xml.etree.ElementTree as ET
from PIL import Image, ImageDraw

SRC = 'public/logo.svg'
OUT_DIR = 'public/icons'
NS = '{http://www.w3.org/2000/svg}'


NAMED = {
    'white': (255, 255, 255),
    'black': (0, 0, 0),
    'red': (255, 0, 0),
    'blue': (0, 0, 255),
    'cyan': (0, 255, 255),
}


def rgb_color(hexstr, opacity=1.0):
    if hexstr.startswith('#'):
        h = hexstr.lstrip('#')
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    else:
        r, g, b = NAMED.get(hexstr.lower(), (255, 255, 255))
    if opacity < 1.0:
        r, g, b = int(r * opacity), int(g * opacity), int(b * opacity)
    return (r, g, b)


def parse_gradient(node):
    stops = []
    for stop in node:
        if stop.tag == NS + 'stop':
            off = float(stop.get('offset', '0').rstrip('%')) / 100.0
            color = stop.get('stop-color', '#000')
            opacity = float(stop.get('stop-opacity', '1'))
            stops.append((off, rgb_color(color, opacity)))
    return stops


def lerp(c0, c1, t):
    return tuple(round(c0[i] + (c1[i] - c0[i]) * t) for i in range(3))


def gradient_at(stops, t):
    stops = sorted(stops)
    if t <= stops[0][0]:
        return stops[0][1]
    if t >= stops[-1][0]:
        return stops[-1][1]
    for i in range(len(stops) - 1):
        o0, c0 = stops[i]
        o1, c1 = stops[i + 1]
        if o0 <= t <= o1:
            if o1 == o0:
                return c0
            return lerp(c0, c1, (t - o0) / (o1 - o0))
    return stops[-1][1]


def project_linear(p, p0, p1, stops):
    dx = p1[0] - p0[0]
    dy = p1[1] - p0[1]
    denom = dx * dx + dy * dy
    if denom == 0:
        return stops[-1][1]
    t = ((p[0] - p0[0]) * dx + (p[1] - p0[1]) * dy) / denom
    t = max(0.0, min(1.0, t))
    return gradient_at(stops, t)


def sample_path(d):
    toks = re.findall(r'[MLCZmlcz]|[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?', d)
    points = []
    current = (0, 0)
    start = (0, 0)
    cmd = None
    args = []
    for t in toks:
        if re.match(r'[MLCZmlcz]', t):
            cmd = t
            args = []
        else:
            args.append(float(t))
            if cmd in ('L', 'l') and len(args) == 2:
                current = ((current[0] + args[0], current[1] + args[1]) if cmd == 'l' else (args[0], args[1]))
                points.append(current)
                args = []
            elif cmd in ('M', 'm') and len(args) == 2:
                current = ((current[0] + args[0], current[1] + args[1]) if cmd == 'm' else (args[0], args[1]))
                start = current
                points.append(current)
                args = []
            elif cmd in ('C', 'c') and len(args) == 6:
                if cmd == 'c':
                    c1 = (current[0] + args[0], current[1] + args[1])
                    c2 = (current[0] + args[2], current[1] + args[3])
                    end = (current[0] + args[4], current[1] + args[5])
                else:
                    c1 = (args[0], args[1])
                    c2 = (args[2], args[3])
                    end = (args[4], args[5])
                for k in range(1, 41):
                    u = k / 40.0
                    x = (1 - u) ** 3 * current[0] + 3 * (1 - u) ** 2 * u * c1[0] + 3 * (1 - u) * u * u * c2[0] + u ** 3 * end[0]
                    y = (1 - u) ** 3 * current[1] + 3 * (1 - u) ** 2 * u * c1[1] + 3 * (1 - u) * u * u * c2[1] + u ** 3 * end[1]
                    points.append((x, y))
                current = end
                args = []
            elif cmd in ('Z', 'z'):
                if points and points[-1] != start:
                    points.append(start)
                current = start
                args = []
    return points


def horizontal_span(poly, y):
    xs = []
    n = len(poly)
    for i in range(n):
        p1 = poly[i]
        p2 = poly[(i + 1) % n]
        if (p1[1] <= y < p2[1]) or (p2[1] <= y < p1[1]):
            t = (y - p1[1]) / (p2[1] - p1[1]) if p2[1] != p1[1] else 0
            xs.append(p1[0] + t * (p2[0] - p1[0]))
    xs.sort()
    spans = []
    for i in range(0, len(xs) - 1, 2):
        spans.append((xs[i], xs[i + 1]))
    return spans


def fill_polygon_gradient(draw, poly, p0, p1, stops):
    ys = [p[1] for p in poly]
    ymin = max(0, int(min(ys)))
    ymax = min(draw._size[1] - 1, int(max(ys)))
    for y in range(ymin, ymax + 1):
        color = project_linear((0, y), p0, p1, stops)
        for (x0, x1) in horizontal_span(poly, y + 0.5):
            draw.line([(max(0, int(x0)), y), (min(draw._size[0] - 1, int(x1)), y)], fill=color)


def render(size):
    tree = ET.parse(SRC)
    root = tree.getroot()
    defs = {}
    for dnode in root.iter(NS + 'defs'):
        for g in dnode:
            if g.tag == NS + 'linearGradient':
                defs['#' + g.get('id')] = parse_gradient(g)

    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    scale = size / 512.0

    def sc(p):
        return (p[0] * scale, p[1] * scale)

    for node in root.iter():
        if node.tag == NS + 'path':
            fill = node.get('fill', 'none')
            pts = [sc(p) for p in sample_path(node.get('d', ''))]
            if fill.startswith('url('):
                stops = defs.get(fill[3:-1])
                if stops:
                    p0 = pts[0]
                    p1 = pts[len(pts) // 2]
                    fill_polygon_gradient(draw, pts, p0, p1, stops)
            elif fill and fill != 'none':
                draw.polygon(pts, fill=rgb_color(fill))

        elif node.tag == NS + 'circle':
            cx, cy, r = float(node.get('cx')), float(node.get('cy')), float(node.get('r'))
            fill = node.get('fill', 'none')
            box = [sc((cx - r, cy - r)), sc((cx + r, cy + r))]
            if fill.startswith('url('):
                stops = defs.get(fill[3:-1], [])
                if stops:
                    draw.ellipse(box, fill=stops[0][1])
            elif fill and fill != 'none':
                draw.ellipse(box, fill=rgb_color(fill))

        elif node.tag == NS + 'line':
            x1, y1 = float(node.get('x1')), float(node.get('y1'))
            x2, y2 = float(node.get('x2')), float(node.get('y2'))
            sw = float(node.get('stroke-width', '1'))
            fill = node.get('stroke', 'none')
            if fill and fill != 'none':
                draw.line([sc((x1, y1)), sc((x2, y2))], fill=rgb_color(fill), width=max(1, int(sw * scale)))

    return img


if __name__ == '__main__':
    os.makedirs(OUT_DIR, exist_ok=True)
    for sz in (192, 512):
        out = os.path.join(OUT_DIR, f'icon-{sz}.png')
        render(sz).save(out)
        print('wrote', out)
