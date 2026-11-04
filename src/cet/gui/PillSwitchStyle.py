# PillSwitchStyle module

# Code destined to defining
# PillSwitchStyle class, a custom
# QProxyStyle used by PipelineGUI.

######################################################################
# imports

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPen
from PyQt6.QtGui import QColor
from PyQt6.QtGui import QBrush
from PyQt6.QtCore import QRectF
from PyQt6.QtGui import QPainter
from PyQt6.QtWidgets import QStyle
from PyQt6.QtWidgets import QProxyStyle
from PyQt6.QtWidgets import QStyleOption

######################################################################
# PillSwitchStyle definition


class PillSwitchStyle(QProxyStyle):
    """
    Custom QProxyStyle that explicitly draws a white circle handle (knob)
    inside QCheckBox indicators to guarantee visibility across platforms.
    """
    def drawPrimitive(self, element, option, painter, widget=None):
        """
        Draws QCheckBox indicator with custom
        white circle knob, overriding the default
        QProxyStyle primitive.

        Args:
            element: QStyle primitive element type.
            option: QStyleOption with rect and state.
            painter: QPainter to draw with.
            widget: Optional QWidget for context.

        Returns:
            None.
        """
        if element == QStyle.PrimitiveElement.PE_IndicatorCheckBox and isinstance(option, QStyleOption):
            painter.save()
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)

            # draw background pill track
            rect = QRectF(option.rect)
            is_checked = bool(option.state & QStyle.StateFlag.State_On)

            track_color = QColor('#1f538d') if is_checked else QColor('#4a4d50')
            border_color = QColor('#1f538d') if is_checked else QColor('#565b5e')

            painter.setBrush(QBrush(track_color))
            painter.setPen(QPen(border_color, 1))
            painter.drawRoundedRect(rect, rect.height() / 2, rect.height() / 2)

            # draw white circle knob
            knob_margin = 2.0
            knob_diameter = rect.height() - (knob_margin * 2)

            if is_checked:
                knob_x = rect.right() - knob_margin - knob_diameter
            else:
                knob_x = rect.left() + knob_margin

            knob_y = rect.top() + knob_margin
            knob_rect = QRectF(knob_x, knob_y, knob_diameter, knob_diameter)

            painter.setBrush(QBrush(QColor('#ffffff')))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(knob_rect)

            painter.restore()
            return

        super().drawPrimitive(element, option, painter, widget)

######################################################################
# end of current module
