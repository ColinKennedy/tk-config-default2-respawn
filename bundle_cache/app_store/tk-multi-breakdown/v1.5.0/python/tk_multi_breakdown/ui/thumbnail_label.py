# Copyright (c) 2013 Shotgun Software Inc.
# 
# CONFIDENTIAL AND PROPRIETARY
# 
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit 
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your 
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights 
# not expressly granted therein are reserved by Shotgun Software Inc.

import os
import sys

from tank.platform.qt import QtCore, QtGui

class ThumbnailLabel(QtGui.QLabel):

    def __init__(self, parent=None):
        QtGui.QLabel.__init__(self, parent)

    def setPixmap(self, pixmap):
        
        # scale the pixmap down to fit
        if pixmap.height() > 40 or pixmap.width() > 60:
            # scale it down to 120x80
            pixmap = pixmap.scaled( QtCore.QSize(60,40), QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
        
        # now slap it on top of a 120x80 transparent canvas
        rendered_pixmap = QtGui.QPixmap(60, 40)
        rendered_pixmap.fill(QtCore.Qt.transparent)

        w_offset = (60 - pixmap.width()) / 2
        h_offset = (40 - pixmap.height()) / 2
        
        painter = QtGui.QPainter(rendered_pixmap)
        painter.drawPixmap(w_offset, h_offset, pixmap)
        painter.end()
        
        # and finally assign it
        QtGui.QLabel.setPixmap(self, rendered_pixmap)
        
