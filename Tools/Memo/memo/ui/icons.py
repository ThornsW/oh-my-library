"""Small native-painted icons used by the Qt UI.

Keeping these in code avoids bundling icon-font packages for four toolbar
symbols. The drawings are intentionally simple at 16-20 px and inherit the
same quiet visual language as the rest of the app.
"""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap


IconPainter = Callable[[QPainter, float, QColor], None]


def icon(name: str, color: str = "#334155", *, size: int = 20) -> QIcon:
    painters: dict[str, IconPainter] = {
        "plus": _paint_plus,
        "search": _paint_search,
        "pin": _paint_pin,
        "settings": _paint_settings,
    }
    try:
        painter = painters[name]
    except KeyError as e:
        raise ValueError(f"Unknown icon: {name}") from e
    return _draw(size, QColor(color), painter)


def app_icon(size: int = 32) -> QIcon:
    return _draw(size, QColor("#2563EB"), _paint_note)


def _draw(size: int, color: QColor, painter_fn: IconPainter) -> QIcon:
    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter_fn(painter, float(size), color)
    painter.end()
    return QIcon(pix)


def _pen(color: QColor, size: float, width: float = 1.8) -> QPen:
    pen = QPen(color)
    pen.setWidthF(max(1.2, size * width / 20.0))
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    return pen


def _paint_plus(p: QPainter, size: float, color: QColor) -> None:
    p.setPen(_pen(color, size, 2.1))
    mid = size / 2.0
    pad = size * 0.28
    p.drawLine(QPointF(mid, pad), QPointF(mid, size - pad))
    p.drawLine(QPointF(pad, mid), QPointF(size - pad, mid))


def _paint_search(p: QPainter, size: float, color: QColor) -> None:
    p.setPen(_pen(color, size, 1.9))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawEllipse(QRectF(size * 0.22, size * 0.20, size * 0.39, size * 0.39))
    p.drawLine(QPointF(size * 0.57, size * 0.57), QPointF(size * 0.78, size * 0.78))


def _paint_pin(p: QPainter, size: float, color: QColor) -> None:
    p.setPen(_pen(color, size, 1.7))
    path = QPainterPath()
    path.moveTo(size * 0.38, size * 0.18)
    path.lineTo(size * 0.66, size * 0.46)
    path.lineTo(size * 0.54, size * 0.58)
    path.lineTo(size * 0.74, size * 0.78)
    path.lineTo(size * 0.70, size * 0.82)
    path.lineTo(size * 0.50, size * 0.62)
    path.lineTo(size * 0.34, size * 0.76)
    path.lineTo(size * 0.30, size * 0.72)
    path.lineTo(size * 0.44, size * 0.56)
    path.lineTo(size * 0.18, size * 0.30)
    path.closeSubpath()
    p.drawPath(path)


def _paint_settings(p: QPainter, size: float, color: QColor) -> None:
    p.setPen(_pen(color, size, 1.5))
    p.setBrush(Qt.BrushStyle.NoBrush)
    cx = cy = size / 2.0
    for i in range(8):
        p.save()
        p.translate(cx, cy)
        p.rotate(i * 45)
        p.drawLine(QPointF(0, -size * 0.38), QPointF(0, -size * 0.30))
        p.restore()
    p.drawEllipse(QRectF(size * 0.31, size * 0.31, size * 0.38, size * 0.38))
    p.drawEllipse(QRectF(size * 0.43, size * 0.43, size * 0.14, size * 0.14))


def _paint_note(p: QPainter, size: float, color: QColor) -> None:
    bg = QColor("#EFF6FF")
    edge = QColor("#93C5FD")
    p.setPen(QPen(edge, max(1.0, size * 0.055)))
    p.setBrush(bg)
    rect = QRectF(size * 0.18, size * 0.14, size * 0.64, size * 0.72)
    p.drawRoundedRect(rect, size * 0.10, size * 0.10)

    p.setPen(_pen(color, size, 1.5))
    for y in (0.36, 0.50, 0.64):
        p.drawLine(QPointF(size * 0.32, size * y), QPointF(size * 0.66, size * y))
