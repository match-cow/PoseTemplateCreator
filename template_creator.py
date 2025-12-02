import json
import os
import sys

import numpy as np
import trimesh
from PyQt5.QtCore import QPointF, QRectF, Qt
from PyQt5.QtGui import (
    QColor,
    QPageLayout,
    QPageSize,
    QPainter,
    QPainterPath,
    QPdfWriter,
    QPen,
    QTransform,
)
from PyQt5.QtWidgets import (
    QAction,
    QApplication,
    QFileDialog,
    QGraphicsPathItem,
    QGraphicsRectItem,
    QGraphicsScene,
    QGraphicsView,
    QMainWindow,
    QMessageBox,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

# --- Constants ---
A3_WIDTH_MM = 420
A3_HEIGHT_MM = 297
SCALE_FACTOR = 5  # Screen pixels per millimeter (for display only)


class MeshSliceItem(QGraphicsPathItem):
    """
    A custom Graphics Item representing a sliced mesh footprint.
    It stores the model name and allows for dragging.
    """

    def __init__(self, path, name, original_transform):
        super().__init__(path)
        self.name = name
        # The to_3D matrix from the slice operation (z-plane to 3D)
        self.original_transform = original_transform

        # Visual settings
        self.setBrush(QColor(200, 200, 200, 150))  # Light gray fill
        self.setPen(QPen(Qt.black, 0.5 * SCALE_FACTOR))

        # Make item movable
        self.setFlags(
            QGraphicsPathItem.ItemIsMovable
            | QGraphicsPathItem.ItemIsSelectable
            | QGraphicsPathItem.ItemSendsGeometryChanges
        )


class TemplateEditor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("3D Slicer & Template Layout")
        self.resize(1200, 900)

        # 1. Setup the Scene (The Paper)
        self.scene = QGraphicsScene()

        # Draw the A3 Sheet boundary
        self.paper_width_px = A3_WIDTH_MM * SCALE_FACTOR
        self.paper_height_px = A3_HEIGHT_MM * SCALE_FACTOR
        self.scene.setSceneRect(0, 0, self.paper_width_px, self.paper_height_px)

        # Visual border for the paper
        paper_rect = QGraphicsRectItem(0, 0, self.paper_width_px, self.paper_height_px)
        paper_rect.setPen(QPen(Qt.black, 2))
        paper_rect.setBrush(QColor(255, 255, 255))
        self.scene.addItem(paper_rect)

        # 2. Setup the View
        self.view = QGraphicsView(self.scene)
        self.view.setRenderHint(QPainter.Antialiasing)
        self.view.setBackgroundBrush(
            QColor(50, 50, 50)
        )  # Dark background outside paper

        # 3. Layout
        layout = QVBoxLayout()
        layout.addWidget(self.view)
        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        # 4. Toolbar
        toolbar = QToolBar("Main Toolbar")
        self.addToolBar(toolbar)

        btn_load = QAction("Add Models", self)
        btn_load.triggered.connect(self.load_models)
        toolbar.addAction(btn_load)

        btn_clear = QAction("Clear All", self)
        btn_clear.triggered.connect(self.clear_items)
        toolbar.addAction(btn_clear)

        toolbar.addSeparator()

        btn_export = QAction("Export PDF & JSON", self)
        btn_export.triggered.connect(self.export_data)
        toolbar.addAction(btn_export)

        # 5. Data Storage
        self.loaded_items = []

    def load_models(self):
        """Opens file dialog to select 3D models."""
        files, _ = QFileDialog.getOpenFileNames(
            self, "Select 3D Models", "", "3D Files (*.ply *.stl *.obj)"
        )

        if not files:
            return

        for file_path in files:
            self.process_mesh(file_path)

    def process_mesh(self, file_path):
        """Loads mesh, slices it, and adds to scene."""
        try:
            filename = os.path.basename(file_path)
            model_name = os.path.splitext(filename)[0]

            # --- Trimesh Logic ---
            mesh = trimesh.load_mesh(file_path)

            # Slice at Z=0
            slice_3d = mesh.section(plane_origin=[0, 0, 0], plane_normal=[0, 0, 1])

            if not slice_3d:
                print(f"Warning: No cross-section found for {filename} at Z=0")
                return

            slice_2d, to_3d_matrix = slice_3d.to_planar()

            # Convert Trimesh Path to Qt QPainterPath
            qt_path = QPainterPath()

            # slice_2d.discrete returns a list of closed polygons (arrays of 2D points)
            # This is cleaner than iterating entities for simple outlines
            for entity in slice_2d.discrete:
                if len(entity) < 2:
                    continue

                # Move to first point (scaled to screen pixels)
                start_pt = entity[0] * SCALE_FACTOR
                qt_path.moveTo(start_pt[0], start_pt[1])

                for i in range(1, len(entity)):
                    pt = entity[i] * SCALE_FACTOR
                    qt_path.lineTo(pt[0], pt[1])

                # Close the loop
                qt_path.closeSubpath()

            # Flip Y-Axis for visual representation?
            # Trimesh 2D is usually geometric (Y up), Qt is Screen (Y down).
            # We apply a scale(1, -1) flip to the path to orient it correctly visually,
            # but we must track this for export.
            transform = QTransform()
            transform.scale(1, -1)
            qt_path = transform.map(qt_path)

            # Create Graphics Item
            item = MeshSliceItem(qt_path, model_name, to_3d_matrix)

            # Center it initially
            center_x = self.paper_width_px / 2
            center_y = self.paper_height_px / 2
            item.setPos(center_x, center_y)

            self.scene.addItem(item)
            self.loaded_items.append(item)

        except Exception as e:
            QMessageBox.critical(
                self, "Error", f"Failed to load {file_path}:\n{str(e)}"
            )

    def clear_items(self):
        for item in self.loaded_items:
            self.scene.removeItem(item)
        self.loaded_items = []

    def export_data(self):
        """Exports the arrangement to PDF and JSON."""
        if not self.loaded_items:
            return

        base_name, _ = QFileDialog.getSaveFileName(
            self, "Export Template", "layout", "PDF Files (*.pdf)"
        )
        if not base_name:
            return

        if base_name.endswith(".pdf"):
            base_name = base_name[:-4]

        pdf_path = f"{base_name}.pdf"
        json_path = f"{base_name}.json"

        # --- 1. Export PDF ---
        writer = QPdfWriter(pdf_path)
        writer.setPageSize(QPageSize(QPageSize.A3))
        writer.setPageOrientation(QPageLayout.Landscape)

        painter = QPainter(writer)

        # Calculate scale to fit Scene Pixel units to PDF logical units
        # PDF Writer typically uses 1200 DPI or similar internal metrics
        # We need to map our Scene Rect (mm * 5) to the Printer Rect
        printer_rect = writer.pageLayout().paintRectPixels(writer.resolution())
        scene_rect = self.scene.sceneRect()

        painter.setRenderHint(QPainter.Antialiasing)
        self.scene.render(painter, target=QRectF(printer_rect), source=scene_rect)
        painter.end()

        # --- 2. Export JSON ---
        output_data = {}

        for item in self.loaded_items:
            # Current position in Screen Pixels
            pos = item.pos()

            # Convert Screen Pixels back to Millimeters
            x_mm = pos.x() / SCALE_FACTOR
            # For Y, graphical origin is Top-Left, but engineering often expects Bottom-Left.
            # Keeping it as PDF coordinates (Top-Left is 0,0, Y increases downwards)
            y_mm = pos.y() / SCALE_FACTOR

            # Get the transformation matrix
            # Start with an Identity Matrix (4x4)
            final_matrix = np.eye(4)

            # Insert the Translation (in mm) based on where user placed it on paper
            final_matrix[0, 3] = x_mm
            final_matrix[1, 3] = y_mm

            # Note: The original 'to_3D' matrix from trimesh maps the local slice frame back to
            # the original object 3D frame.
            # If the JSON needs to represent "Where is the object on the paper?", the
            # translation matrix we just built above is usually sufficient.
            # However, if you need to combine the rotation of the slice, we would need logic here.
            # BASED ON YOUR EXAMPLE: You output a 4x4 matrix.
            # I will output the matrix representing the position on the A3 sheet.

            output_data[item.name] = final_matrix.tolist()

        with open(json_path, "w") as f:
            json.dump(output_data, f, default=str, indent=4)

        QMessageBox.information(
            self, "Success", f"Exported to:\n{pdf_path}\n{json_path}"
        )


def main():
    app = QApplication(sys.argv)
    window = TemplateEditor()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
