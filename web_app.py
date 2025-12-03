import io
import json
import os
import tempfile

import matplotlib.pyplot as plt
import numpy as np
import streamlit as st
import trimesh
from reportlab.lib.pagesizes import A0, A1, A2, A3, A4, landscape
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

st.set_page_config(page_title="Pose Template Creator", page_icon="assets/match.png")

# Constants
# Use reportlab's precise page sizes converted to mm
factor = 25.4 / 72
PAGE_SIZES = {
    "A4": tuple(dim * factor for dim in landscape(A4)),  # landscape: width x height mm
    "A3": tuple(dim * factor for dim in landscape(A3)),
    "A2": tuple(dim * factor for dim in landscape(A2)),
    "A1": tuple(dim * factor for dim in landscape(A1)),
    "A0": tuple(dim * factor for dim in landscape(A0)),
}
SCALE_FACTOR = 5  # For display, but we'll use mm directly

# Title with logo on the right
col1, col2 = st.columns([4, 1])
with col1:
    st.title("Pose Template Creator")
with col2:
    st.image("assets/match.png", width=80)

# Page size selection
page_size = st.selectbox(
    "Select Page Size",
    options=list(PAGE_SIZES.keys()),
    index=list(PAGE_SIZES.keys()).index(st.session_state.get("page_size", "A3")),
)
st.session_state.page_size = page_size
page_width, page_height = PAGE_SIZES[page_size]

# Template name input
template_name = st.text_input(
    "Template Name",
    value=st.session_state.get("template_name", ""),
    placeholder="Enter template name for downloads",
)
st.session_state.template_name = template_name

# Initialize session state
if "loaded_objects" not in st.session_state:
    st.session_state.loaded_objects = []
if "page_size" not in st.session_state:
    st.session_state.page_size = "A3"
if "template_name" not in st.session_state:
    st.session_state.template_name = ""

# File upload
uploaded_files = st.file_uploader(
    "Upload 3D Models", type=["ply", "stl", "obj"], accept_multiple_files=True
)

if uploaded_files:
    if st.button("Load Models"):
        for uploaded_file in uploaded_files:
            # Save to temp file, removing texture references if PLY
            content = uploaded_file.getvalue()
            if uploaded_file.name.lower().endswith(".ply"):
                # Check if ASCII PLY to safely remove texture references
                header = content[:200].decode("utf-8", errors="ignore")
                if "format ascii" in header.lower():
                    # Remove lines containing .png to avoid texture loading errors
                    lines = content.decode("utf-8", errors="ignore").split("\n")
                    lines = [line for line in lines if ".png" not in line.lower()]
                    content = "\n".join(lines).encode("utf-8")
                # For binary PLY, leave content unchanged

            with tempfile.NamedTemporaryFile(
                delete=False, suffix=os.path.splitext(uploaded_file.name)[1]
            ) as tmp:
                tmp.write(content)
                tmp_path = tmp.name

            try:
                # Load mesh
                mesh = trimesh.load_mesh(tmp_path)

                # Slice at Z=0
                slice_3d = mesh.section(plane_origin=[0, 0, 0], plane_normal=[0, 0, 1])

                if slice_3d:
                    slice_2d, to_3d_matrix = slice_3d.to_2D()

                    # Get polygons
                    polygons = []
                    for entity in slice_2d.discrete:
                        if len(entity) > 2:
                            poly = entity.tolist()
                            polygons.append(poly)

                    if polygons:
                        name = os.path.splitext(uploaded_file.name)[0]
                        # Initial position at center
                        initial_x = page_width / 2
                        initial_y = page_height / 2

                        obj = {
                            "name": name,
                            "polygons": polygons,
                            "position": [initial_x, initial_y],
                            "rotation": 0.0,
                            "to_3d_matrix": to_3d_matrix,
                        }
                        st.session_state.loaded_objects.append(obj)

            except Exception as e:
                st.error(f"Error loading {uploaded_file.name}: {str(e)}")
            finally:
                os.unlink(tmp_path)

        st.success(f"Loaded {len(st.session_state.loaded_objects)} models")

# Display loaded objects and controls
if st.session_state.loaded_objects:
    st.header("Arrange Objects")

    for i, obj in enumerate(st.session_state.loaded_objects):
        st.subheader(f"Object: {obj['name']}")

        col1, col2, col3 = st.columns(3)
        with col1:
            slider_x = st.slider(
                f"X Position (mm) for {obj['name']}",
                0.0,
                float(page_width - 30),
                float(obj["position"][0] - 15),
                key=f"x_{i}",
            )
            obj["position"][0] = slider_x + 15
        with col2:
            slider_y = st.slider(
                f"Y Position (mm) for {obj['name']}",
                0.0,
                float(page_height - 30),
                float(obj["position"][1] - 15),
                key=f"y_{i}",
            )
            obj["position"][1] = slider_y + 15
        with col3:
            obj["rotation"] = st.slider(
                f"Rotation (deg) for {obj['name']}",
                -180.0,
                180.0,
                float(obj["rotation"]),
                key=f"rot_{i}",
            )

    # Generate preview
    fig, ax = plt.subplots(figsize=(page_width / 25.4, page_height / 25.4))  # inches
    ax.axis("off")
    ax.set_xlim(0, page_width)
    ax.set_ylim(0, page_height)
    ax.set_aspect("equal")

    # Draw coordinate system like in PDF
    # X axis red
    ax.plot([15, page_width - 15], [15, 15], color="red", linewidth=1)
    # Y axis green
    ax.plot([15, 15], [15, page_height - 15], color="green", linewidth=1)
    # Arrows for X
    arrow_size = 5
    ax.plot(
        [page_width - 15, page_width - 15 - arrow_size],
        [15, 15 - arrow_size / 2],
        color="red",
        linewidth=1,
    )
    ax.plot(
        [page_width - 15, page_width - 15 - arrow_size],
        [15, 15 + arrow_size / 2],
        color="red",
        linewidth=1,
    )
    # Arrows for Y
    ax.plot(
        [15, 15 - arrow_size / 2],
        [page_height - 15, page_height - 15 - arrow_size],
        color="green",
        linewidth=1,
    )
    ax.plot(
        [15, 15 + arrow_size / 2],
        [page_height - 15, page_height - 15 - arrow_size],
        color="green",
        linewidth=1,
    )
    # Labels
    ax.text(page_width - 25, 20, "X", fontsize=12, color="red")
    ax.text(20, page_height - 25, "Y", fontsize=12, color="green")
    ax.text(20, 20, "Z", fontsize=12, color="blue")
    # Origin dot
    ax.plot(15, 15, "bo", markersize=5)
    ax.plot(15, 15, "ko", markersize=2)
    # Ticks
    # X ticks
    for i in range(25, int(page_width) - 15 - 10 + 1, 10):
        ax.plot([i, i], [15, 15 + 2], color="red", linewidth=0.5)
    # Y ticks
    for i in range(25, int(page_height) - 15 - 10 + 1, 10):
        ax.plot([15, 15 + 2], [i, i], color="green", linewidth=0.5)
    # Border
    rect = plt.Rectangle(
        (0, 0),
        page_width,
        page_height,
        linewidth=0.5,
        edgecolor="black",
        facecolor="none",
    )
    ax.add_patch(rect)

    # Draw objects
    for obj in st.session_state.loaded_objects:
        x_offset, y_offset = obj["position"]
        theta = np.radians(obj.get("rotation", 0))
        for poly in obj["polygons"]:
            # Rotate and shift polygon
            rotated_poly = [
                [
                    p[0] * np.cos(theta) - p[1] * np.sin(theta),
                    p[0] * np.sin(theta) + p[1] * np.cos(theta),
                ]
                for p in poly
            ]
            shifted_poly = [(p[0] + x_offset, p[1] + y_offset) for p in rotated_poly]
            ax.fill(
                *zip(*shifted_poly), alpha=0.3, edgecolor="black", facecolor="lightgray"
            )
        # Draw origin dot at the object's position
        ax.plot(x_offset, y_offset, "bo", markersize=5)

    st.pyplot(fig)

    # Export buttons
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Export PDF"):
            # Generate PDF
            buffer = io.BytesIO()
            c = canvas.Canvas(buffer, pagesize=(page_width * mm, page_height * mm))

            # Add template name in top right corner with 10mm padding
            if st.session_state.template_name:
                c.setFillColorRGB(0, 0, 0)
                c.drawRightString(
                    (page_width - 10) * mm,
                    (page_height - 10) * mm,
                    st.session_state.template_name,
                )

            # Draw objects
            for obj in st.session_state.loaded_objects:
                x_offset, y_offset = obj["position"]
                theta = np.radians(obj.get("rotation", 0))
                for poly in obj["polygons"]:
                    rotated_poly = [
                        [
                            p[0] * np.cos(theta) - p[1] * np.sin(theta),
                            p[0] * np.sin(theta) + p[1] * np.cos(theta),
                        ]
                        for p in poly
                    ]
                    shifted_poly = [
                        (p[0] + x_offset, p[1] + y_offset) for p in rotated_poly
                    ]
                    if shifted_poly:
                        c.setFillColorRGB(0.8, 0.8, 0.8, 0.5)
                        c.setStrokeColorRGB(0, 0, 0)
                        path = c.beginPath()
                        path.moveTo(shifted_poly[0][0] * mm, shifted_poly[0][1] * mm)
                        for p in shifted_poly[1:]:
                            path.lineTo(p[0] * mm, p[1] * mm)
                        path.close()
                        c.drawPath(path, fill=1, stroke=1)

                # Draw origin dot at the object's position
                c.setFillColorRGB(0, 0, 1)  # blue
                c.circle(x_offset * mm, y_offset * mm, 2 * mm, fill=1)
                c.setFillColorRGB(0, 0, 0)  # black
                c.circle(x_offset * mm, y_offset * mm, 0.5 * mm, fill=1)

            # Draw coordinate system (with 15mm padding)
            c.setLineWidth(1)  # Thinner
            # X axis red
            c.setStrokeColorRGB(1, 0, 0)
            x_start_x = 15 * mm
            x_start_y = 15 * mm
            x_end_x = (page_width - 15) * mm
            x_end_y = 15 * mm
            c.line(x_start_x, x_start_y, x_end_x, x_end_y)
            # Arrow for x
            arrow_size = 5 * mm
            c.line(x_end_x, x_end_y, x_end_x - arrow_size, x_end_y - arrow_size / 2)
            c.line(x_end_x, x_end_y, x_end_x - arrow_size, x_end_y + arrow_size / 2)
            # Y axis green
            c.setStrokeColorRGB(0, 1, 0)
            y_start_x = 15 * mm
            y_start_y = 15 * mm
            y_end_x = 15 * mm
            y_end_y = (page_height - 15) * mm
            c.line(y_start_x, y_start_y, y_end_x, y_end_y)
            # Arrow for y
            c.line(y_end_x, y_end_y, y_end_x - arrow_size / 2, y_end_y - arrow_size)
            c.line(y_end_x, y_end_y, y_end_x + arrow_size / 2, y_end_y - arrow_size)
            # Labels
            c.setFillColorRGB(1, 0, 0)
            c.drawString((page_width - 25) * mm, 20 * mm, "X")
            c.setFillColorRGB(0, 1, 0)
            c.drawString(20 * mm, (page_height - 25) * mm, "Y")
            # Ticks every 10mm
            c.setLineWidth(0.5)
            # X ticks
            c.setStrokeColorRGB(1, 0, 0)  # red
            for i in range(25, int(page_width) - 15 - 10 + 1, 10):
                c.line(i * mm, 15 * mm, i * mm, 15 * mm + 2 * mm)
            # Y ticks
            c.setStrokeColorRGB(0, 1, 0)  # green
            for i in range(25, int(page_height) - 15 - 10 + 1, 10):
                c.line(15 * mm, i * mm, 15 * mm + 2 * mm, i * mm)

            # Origin dot with Z label
            c.setFillColorRGB(0, 0, 1)  # blue
            c.setStrokeColorRGB(0, 0, 0)  # black border
            c.circle(15 * mm, 15 * mm, 2 * mm, fill=1, stroke=1)
            c.setFillColorRGB(0, 0, 0)  # black
            c.circle(15 * mm, 15 * mm, 0.5 * mm, fill=1)
            c.setFillColorRGB(0, 0, 1)  # blue
            c.drawString(20 * mm, 20 * mm, "Z")

            # Add thin black border at page edge
            c.setLineWidth(0.5)
            c.setStrokeColorRGB(0, 0, 0)
            c.rect(0, 0, page_width * mm, page_height * mm)

            c.save()
            buffer.seek(0)
            pdf_filename = (
                f"{st.session_state.template_name}.pdf"
                if st.session_state.template_name
                else "layout.pdf"
            )
            st.download_button("Download PDF", buffer, pdf_filename, "application/pdf")

    with col2:
        if st.button("Export JSON"):
            output_data = {}
            for obj in st.session_state.loaded_objects:
                x_mm, y_mm = obj["position"]
                theta = np.radians(obj.get("rotation", 0))
                cos_t = np.cos(theta)
                sin_t = np.sin(theta)
                rotation_matrix = np.array(
                    [
                        [cos_t, -sin_t, 0, 0],
                        [sin_t, cos_t, 0, 0],
                        [0, 0, 1, 0],
                        [0, 0, 0, 1],
                    ]
                )
                translation_matrix = np.eye(4)
                translation_matrix[0, 3] = x_mm - 15
                translation_matrix[1, 3] = y_mm - 15
                final_matrix = translation_matrix @ rotation_matrix
                output_data[obj["name"]] = final_matrix.tolist()

            json_str = json.dumps(output_data, indent=4)
            json_filename = (
                f"{st.session_state.template_name}.json"
                if st.session_state.template_name
                else "layout.json"
            )
            st.download_button(
                "Download JSON", json_str, json_filename, "application/json"
            )

if st.button("Clear All"):
    st.session_state.loaded_objects = []
    st.rerun()
