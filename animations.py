from PyQt5.QtCore import (QPropertyAnimation, QEasingCurve, 
                         QRect, QPoint, QAbstractAnimation)
from PyQt5.QtWidgets import QGraphicsOpacityEffect

class SlideAnimation:
    def __init__(self, widget, parent=None):
        self.widget = widget
        self.parent = parent
        self.animation = QPropertyAnimation(self.widget, b"geometry")
        self.animation.setEasingCurve(QEasingCurve.OutQuint)
        self.animation.setDuration(350)
        
    def setup(self, start_geometry, end_geometry):
        self.animation.setStartValue(start_geometry)
        self.animation.setEndValue(end_geometry)
        
    def start(self, direction='forward'):
        if direction == 'forward':
            self.widget.show()
        self.animation.start(QAbstractAnimation.DeleteWhenStopped)
        
    def reverse(self):
        self.animation.setDirection(QAbstractAnimation.Backward)
        self.start()

class FadeAnimation:
    def __init__(self, widget):
        self.widget = widget
        self.effect = QGraphicsOpacityEffect()
        self.widget.setGraphicsEffect(self.effect)
        self.animation = QPropertyAnimation(self.effect, b"opacity")
        self.animation.setDuration(300)
        
    def fade_in(self):
        self.animation.setStartValue(0)
        self.animation.setEndValue(1)
        self.widget.show()
        self.animation.start()
        
    def fade_out(self):
        self.animation.setStartValue(1)
        self.animation.setEndValue(0)
        self.animation.finished.connect(lambda: self.widget.hide())
        self.animation.start()

class HoverAnimation:
    def __init__(self, widget):
        self.widget = widget
        self.animation = QPropertyAnimation(widget, b"geometry")
        self.animation.setDuration(200)
        self.animation.setEasingCurve(QEasingCurve.OutQuad)
        self.original_geom = None
        self.scale_factor = 1.03
        
    def setup_animation(self, enlarge=True):
        if not self.original_geom:
            self.original_geom = self.widget.geometry()
            
        center = self.original_geom.center()
        width = self.original_geom.width()
        height = self.original_geom.height()
        
        if enlarge:
            new_width = width * self.scale_factor
            new_height = height * self.scale_factor
            new_geom = QRect(
                int(center.x() - new_width / 2),
                int(center.y() - new_height / 2),
                int(new_width),
                int(new_height)
            )
        else:
            new_geom = self.original_geom
            
        self.animation.stop()
        self.animation.setStartValue(self.widget.geometry())
        self.animation.setEndValue(new_geom)
        self.animation.start()
