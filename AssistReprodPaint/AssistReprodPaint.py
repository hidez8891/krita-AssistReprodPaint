from PyQt5 import QtWidgets, Qt
from PyQt5.QtCore import QByteArray
from PyQt5.QtGui import QImage
from krita import *
from urllib import request, error


class InputUrlDialog(QtWidgets.QDialog):

    def __init__(self):
        super().__init__()

        layout = QtWidgets.QFormLayout(self)

        self.url_input = QtWidgets.QLineEdit(self)
        layout.addRow("URL", self.url_input)

        buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel, self)
        layout.addWidget(buttons)

        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

    def getURL(self) -> str:
        return self.url_input.text()


class AssistReprodPaint(Extension):

    def __init__ (self, parent):
        super().__init__(parent)

    def setup(self):
        pass

    def createActions(self, window: Window):
        action = window.createAction("AssitRepordPaint-start", "start Reprod-Painting")
        action.triggered.connect(self.doCreateView)
        action.triggered.connect(self.doSetGrid)
        action.triggered.connect(self.doSplitView)

    def downloadImage(self) -> QImage | None:
        # input URL
        url_dialog = InputUrlDialog()
        if url_dialog.exec_() == QtWidgets.QDialog.DialogCode.Rejected:
            return None
        url = url_dialog.getURL()

        # download Image
        try:
            req = request.Request(url)
            with request.urlopen(req) as res:
                img_qt = QImage()
                img_qt.loadFromData(res.read())
        except error.HTTPError as e:
            # TODO ERROR Message
            return None
        return img_qt

    def scaleImage(self, img: QImage) -> QImage | None:
        app = Krita.instance()

        # load default parameter
        default_width = int(app.readSetting("", "imageWidthDef", "-1"))
        default_height = int(app.readSetting("", "imageHeightDef", "-1"))
        if default_width < 0 or default_height < 0:
            # TODO ERROR Message
            return None

        # scale image
        scale_x = default_width / float(img.width())
        scale_y = default_height / float(img.height())
        if scale_x > scale_y:
            return img.scaledToWidth(default_width, 1)
        else:
            return img.scaledToHeight(default_height, 1)


    def appendNewView(self, view_name: str, width: int, height: int,
                      color_model: str = "",
                      color_depth: str = "",
                      profile: str = "",
                      resolution: float = -1,
                      ) -> View:
        app = Krita.instance()

        # load default parameter
        if color_model == "":
            color_model = app.readSetting("", "colorModelDef", "")
            if color_model == "":
                # TODO ERROR Message
                return
        if color_depth == "":
            color_depth = app.readSetting("", "colorDepthDef", "")
            if color_depth == "":
                # TODO ERROR Message
                return
        if profile == "":
            profile = app.readSetting("", "colorProfileDef", "")
            if profile == "":
                # TODO ERROR Message
                return
        if resolution < 0:
            resolution = float(app.readSetting("", "imageResolutionDef", "-1"))
            if resolution < 0:
                # TODO ERROR Message
                return

        # add new document
        doc = app.createDocument(width, height,
                                 view_name, color_model, color_depth,
                                 profile, resolution)
        view = app.activeWindow().addView(doc)

        # set document's node
        node = doc.createNode("paint 1", "paintlayer")
        doc.rootNode().addChildNode(node, None)
        doc.setActiveNode(node)
        doc.refreshProjection()
        return view

    def copyImageToView(self, img, view):
        node = view.document().nodeByName("paint 1")
        node.setPixelData(QByteArray(img.bits().asstring(img.byteCount())), 0, 0, img.width(), img.height())
        node.projectionPixelData(0, 0, img.width(), img.height())
        view.document().refreshProjection()

    def doCreateView(self):
        # download Image
        img = self.downloadImage()
        if img == None:
            return
        # scale Image
        img = self.scaleImage(img)
        if img == None:
            return

        # create Target Image Document
        target_view = self.appendNewView("Download Image", img.width(), img.height())
        self.copyImageToView(img, target_view)

        # create Draw Image Document
        draw_view = self.appendNewView("Draw Image", img.width(), img.height())

    def doSetGrid(self):
        # reference: https://github.com/kedepot/keKit-Krita
        app = Krita.instance()
        win = app.activeWindow()
        qwin = app.activeWindow().qwindow()

        for view in win.views():
            view.setVisible()
            doc = view.document()

            docker = qwin.findChild(QtWidgets.QDockWidget, 'GridDocker')
            grid_show = docker.findChild(QtWidgets.QCheckBox, 'chkShowGrid')
            grid_snap = docker.findChild(QtWidgets.QCheckBox, 'chkSnapToGrid')

            if not grid_show.isChecked():
                grid_show.setCheckState(True)
            if not grid_snap.isChecked():
                grid_snap.setCheckState(True)

            factor_x = 1.0/3.0
            factor_y = 1.0/3.0

            aspect_lock = docker.findChild(QtWidgets.QAbstractButton, 'spacingAspectButton')
            grid_div = docker.findChild(QtWidgets.QWidget, 'intSubdivision')
            x_spacing = docker.findChild(QtWidgets.QWidget, 'intHSpacing')
            y_spacing = docker.findChild(QtWidgets.QWidget, 'intVSpacing')

            new_x = int(doc.width() * factor_x)
            new_y = int(doc.width() * factor_y)
            x_spacing.setValue(new_x)
            y_spacing.setValue(new_y)

            # Check if the correct values have been applied:
            x_spacing = docker.findChild(QtWidgets.QWidget, 'intHSpacing')
            y_spacing = docker.findChild(QtWidgets.QWidget, 'intVSpacing')
            if x_spacing.value() != new_x or y_spacing.value() != new_y:
                # ...then 2nd try with fake-click
                aspect_lock.click()
                x_spacing.setValue(new_x)
                y_spacing.setValue(new_y)

            # Apply grid settings
            grid_div.setValue(1)
            grid_show.setCheckState(True)

    def doSplitView(self):
        app = Krita.instance()
        mode = int(app.readSetting("", "mdi_viewmode", "-1"))
        if mode != 0:
            # TODO ERROR Message
            return
        app.action('windows_tile').activate(0)


Krita.instance().addExtension(AssistReprodPaint(Krita.instance()))
