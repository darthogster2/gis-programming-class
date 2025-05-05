# -*- coding: utf-8 -*-
import os
from qgis.PyQt import uic
from qgis.PyQt.QtWidgets import QDialog, QMessageBox
from qgis.gui import QgsFileWidget, QgsMapLayerComboBox
from qgis.core import QgsProject, QgsMapLayerProxyModel  # Импорт из core!

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'tselovalnikov_dialog_base.ui'))


class TselovalnikovDialog(QDialog, FORM_CLASS):
    def __init__(self, parent=None):
        super(TselovalnikovDialog, self).__init__(parent)
        self.setupUi(self)

        # Правильная настройка фильтра слоев
        self.layer_combo.setFilters(QgsMapLayerProxyModel.VectorLayer)
        self.layer_combo.setAllowEmptyLayer(False)

        self.spnRadius.setSuffix(" м")
        self.spnRadius.setValue(100.0)
        self.spnRadius.setMinimum(0.1)
        self.spnRadius.setMaximum(10000.0)

        self.fileWidget.setStorageMode(QgsFileWidget.SaveFile)
        self.fileWidget.setFilter("GeoTIFF files (*.tif *.tiff)")
        self.btnCalculate.clicked.connect(self._validate_and_accept)
        self.button_box.accepted.connect(self._validate_and_accept)
        self.button_box.rejected.connect(self.reject)

    def _validate_and_accept(self):
        if not self.layer_combo.currentLayer():
            QMessageBox.warning(self, "Ошибка", "Не выбран слой")
            return
        if self.spnRadius.value() <= 0:
            QMessageBox.warning(self, "Ошибка", "Радиус должен быть положительным числом")
            return
        self.accept()

    def get_parameters(self):
        return {
            'layer': self.layer_combo.currentLayer(),
            'radius': self.spnRadius.value(),
            'output_path': self.fileWidget.filePath() or None
        }