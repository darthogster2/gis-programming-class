# -*- coding: utf-8 -*-
import os
import csv
import time
from qgis.PyQt.QtCore import QSettings, QTranslator, QCoreApplication, Qt, QTimer
from qgis.PyQt.QtGui import QIcon, QColor
from qgis.PyQt.QtWidgets import QAction, QProgressDialog
from qgis.core import (
    QgsProject, QgsVectorLayer, QgsRasterLayer,
    QgsProcessingFeedback, QgsGradientColorRamp,
    QgsRasterShader, QgsColorRampShader,
    QgsSingleBandPseudoColorRenderer,
    QgsCoordinateReferenceSystem,
    QgsColorRampShader
)
from qgis.analysis import QgsNativeAlgorithms
from .tselovalnikov_dialog import TselovalnikovDialog
import processing


class Tselovalnikov:
    def __init__(self, iface):
        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'Tselovalnikov_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)
            QCoreApplication.installTranslator(self.translator)

        self.actions = []
        self.menu = self.tr(u'&Tselovalnikov Density Analyzer')
        self.first_start = None

    def tr(self, message):
        return QCoreApplication.translate('Tselovalnikov', message)

    def add_action(
            self,
            icon_path,
            text,
            callback,
            enabled_flag=True,
            add_to_menu=True,
            add_to_toolbar=True,
            status_tip=None,
            whats_this=None,
            parent=None):

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            self.iface.addToolBarIcon(action)

        if add_to_menu:
            self.iface.addPluginToMenu(
                self.menu,
                action)

        self.actions.append(action)
        return action

    def initGui(self):
        icon_path = ':/plugins/tselovalnikov/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'Density Analyzer'),
            callback=self.run,
            parent=self.iface.mainWindow())

        self.first_start = True

    def unload(self):
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&Tselovalnikov Density Analyzer'),
                action)
            self.iface.removeToolBarIcon(action)

    def run(self):
        if self.first_start:
            self.first_start = False
            self.dlg = TselovalnikovDialog()
            self.dlg.setWindowTitle(self.tr("Анализатор плотности объектов"))

        self.dlg.show()
        if self.dlg.exec_():
            self.analyze_density()

    def cleanup_temp_file(self, file_path):
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except PermissionError:
                QTimer.singleShot(5000, lambda: self.cleanup_temp_file(file_path))
            except Exception as e:
                self.iface.messageBar().pushWarning(
                    "Очистка",
                    f"Не удалось удалить файл: {str(e)}"
                )

    def analyze_density(self):
        input_layer = self.dlg.layer_combo.currentLayer()
        radius = float(self.dlg.spnRadius.value())
        output_path = self.dlg.fileWidget.filePath()

        if not input_layer or not input_layer.isValid():
            self.iface.messageBar().pushCritical("Ошибка", "Неверный входной слой")

        
        if input_layer.crs().isGeographic():
            params = {
                'INPUT': input_layer,
                'TARGET_CRS': QgsCoordinateReferenceSystem('EPSG:3857'),
                'OUTPUT': 'memory:'
            }
            input_layer = processing.run("native:reprojectlayer", params)['OUTPUT']
        for layer in QgsProject.instance().mapLayersByName("Тепловая карта"):
            QgsProject.instance().removeMapLayer(layer.id())

        temp_file = os.path.join(
            QgsProject.instance().homePath(),
            f"heatmap_{os.getpid()}_{int(time.time())}.tif"
        )

        try:
            params = {
                'INPUT': input_layer,
                'RADIUS': radius,
                'PIXEL_SIZE': radius / 10,
                'TARGET_CRS': QgsCoordinateReferenceSystem('EPSG:3857'),
                'OUTPUT': temp_file,
                'FORMAT': 1
            }

            result = processing.run("qgis:heatmapkerneldensityestimation", params)
            print("Результат:", result) 

            # Загрузка слоя
            if result['OUTPUT'] and os.path.exists(result['OUTPUT']):
                density_layer = QgsRasterLayer(result['OUTPUT'], "Тепловая карта")
                if density_layer.isValid():
                    QgsProject.instance().addMapLayer(density_layer)
                    self.apply_heatmap_style(density_layer)
                    self.iface.messageBar().pushSuccess("Норм", "Тепловая карта создана")
                else:
                    self.iface.messageBar().pushCritical("Ошибка", "Не работает")
            else:
                self.iface.messageBar().pushCritical("Ошибка", "Файл не создан")

        except Exception as e:
            self.iface.messageBar().pushCritical("Ошибка", f"Детали: {str(e)}")

        finally:
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except Exception as e:
                    print(f"Ошибка удаления файла: {e}")

    def cleanup_temp_file(self, file_path):
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except PermissionError:
                QTimer.singleShot(5000, lambda: self.cleanup_temp_file(file_path))
            except Exception as e:
                self.iface.messageBar().pushInfo(
                    "Очистка",
                    f"Файл {os.path.basename(file_path)} не был удален: {str(e)}"
                )

    def apply_heatmap_style(self, layer):
        ramp = QgsColorRampShader()
        ramp.setColorRampType(QgsColorRampShader.Interpolated)
        ramp.setColorRampItemList([
            QgsColorRampShader.ColorRampItem(0, QColor(0, 0, 255, 0), "Min"),
            QgsColorRampShader.ColorRampItem(0.2, QColor(0, 0, 255)),
            QgsColorRampShader.ColorRampItem(0.5, QColor(0, 255, 0)),
            QgsColorRampShader.ColorRampItem(0.8, QColor(255, 255, 0)),
            QgsColorRampShader.ColorRampItem(1, QColor(255, 0, 0), "Max")
        ])


        renderer = QgsSingleBandPseudoColorRenderer(layer.dataProvider(), 1)
        shader = QgsRasterShader()
        shader.setRasterShaderFunction(ramp)
        renderer.setShader(shader)
        layer.setRenderer(renderer)
        layer.triggerRepaint()
        
    def export_stats(self, layer, radius, path):
        try:
            with open(path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(['Параметр', 'Значение'])
                writer.writerow(['Слой', layer.name()])
                writer.writerow(['Тип геометрии', layer.geometryType()])
                writer.writerow(['CRS', layer.crs().authid()])
                writer.writerow(['Радиус анализа (м)', radius])
                writer.writerow(['Кол-во объектов', layer.featureCount()])
                writer.writerow(['Дата анализа', time.strftime("%Y-%m-%d %H:%M:%S")])

            self.iface.messageBar().pushSuccess(
                "Экспорт",
                f"сохранено в {path}"
            )
        except Exception as e:
            self.iface.messageBar().pushWarning(
                "Ошибка экспорта",
                f"Не удалось: {str(e)}"
            )