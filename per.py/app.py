```python
import streamlit as st
from PIL import Image
import img2pdf
import io
import zipfile
import cv2
import numpy as np
import fitz  # PyMuPDF
from pypdf import PdfReader, PdfWriter
import base64

# Configure page
st.set_page_config(
    page_title="Multi-Purpose File Processor",
    page_icon="🔧",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .feature-box {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 10px;
        margin: 1rem 0;
    }
    .success-msg {
        background-color: #d4edda;
        color: #155724;
        padding: 0.75rem;
        border-radius: 5px;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# ===== Helper Functions =====
def create_download_link(data, filename, text="Download"):
    b64 = base64.b64encode(data).decode()
    href = f'<a href="data:application/octet-stream;base64,{b64}" download="{filename}">{text}</a>'
    return href

# ===== PDF to Image with PyMuPDF =====
def pdf_to_images_pymupdf(pdf_bytes, dpi=200, image_format="PNG"):
    """Convert PDF to list of images using PyMuPDF"""
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        images = []
        for page_num in range(len(doc)):
            page = doc[page_num]
            pix = page.get_pixmap(dpi=dpi)
            img_bytes = pix.tobytes(image_format.lower())
            img = Image.open(io.BytesIO(img_bytes))
            images.append(img)
        return images
    except Exception as e:
        st.error(f"Error converting PDF: {e}")
        return None

# ===== Security Functions =====
def encrypt_pdf(pdf_bytes, user_password, owner_password=None):
    try:
        pdf_stream = io.BytesIO(pdf_bytes)
        reader = PdfReader(pdf_stream)
        writer = PdfWriter()
        for page in reader.pages:
            writer.add_page(page)
        writer.encrypt(
            user_password=user_password,
            owner_password=owner_password or user_password,
            algorithm="AES-256"
        )
        output = io.BytesIO()
        writer.write(output)
        output.seek(0)
        return output.read()
    except Exception as e:
        st.error(f"Encryption error: {e}")
        return None

def decrypt_pdf(encrypted_pdf_bytes, password):
    try:
        reader = PdfReader(io.BytesIO(encrypted_pdf_bytes))
        if reader.is_encrypted:
            if reader.decrypt(password):
                writer = PdfWriter()
                for page in reader.pages:
                    writer.add_page(page)
                output = io.BytesIO()
                writer.write(output)
                output.seek(0)
                return output.read()
            else:
                st.error("Incorrect password")
                return None
        else:
            st.info("PDF is not encrypted")
            return encrypted_pdf_bytes
    except Exception as e:
        st.error(f"Decryption error: {e}")
        return None

# ===== Image Processing =====
def resize_image(image_file, width, height):
    try:
        img = Image.open(image_file)
        resized_img = img.resize((width, height), Image.Resampling.LANCZOS)
        img_byte_arr = io.BytesIO()
        img_format = img.format if img.format else 'PNG'
        resized_img.save(img_byte_arr, format=img_format)
        img_byte_arr.seek(0)
        return img_byte_arr.getvalue(), img_format.lower()
    except Exception as e:
        st.error(f"Resize error: {e}")
        return None, None

def compress_image(image_file, quality=85):
    try:
        img = Image.open(image_file)
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format="JPEG", quality=quality, optimize=True)
        img_byte_arr.seek(0)
        return img_byte_arr.getvalue()
    except Exception as e:
        st.error(f"Compression error: {e}")
        return None

# ===== FIXED Images to PDF (handles invalid EXIF rotation) =====
def images_to_pdf_conversion(image_files):
    try:
        pil_images = []
        for img_file in image_files:
            img = Image.open(img_file)
            rgb_img = img.convert("RGB")  # normalize mode
            temp_io = io.BytesIO()
            rgb_img.save(temp_io, format="JPEG")
            temp_io.seek(0)
            pil_images.append(temp_io.read())
        pdf_bytes = img2pdf.convert(pil_images, rotation=img2pdf.Rotation.ifvalid)
        return pdf_bytes
    except Exception as e:
        st.error(f"Error creating PDF: {e}")
        return None

# ===== Main App =====
def main():
    st.markdown('<h1 class="main-header">🔧 Multi-Purpose File Processor</h1>', unsafe_allow_html=True)
    st.markdown("**Transform, Edit, Secure & Process PDFs and Images with Advanced Features**")

    st.sidebar.title("🚀 Operations")
    operation = st.sidebar.selectbox(
        "Choose operation:",
        ["📄 PDF to Images", "🖼️ Images to PDF", "📏 Resize Images",
         "🗜️ Compress Images", "🔒 PDF Security"]
    )

    if operation == "📄 PDF to Images":
        pdf_to_images_interface()
    elif operation == "🖼️ Images to PDF":
        images_to_pdf_interface()
    elif operation == "📏 Resize Images":
        resize_images_interface()
    elif operation == "🗜️ Compress Images":
        compress_images_interface()
    elif operation == "🔒 PDF Security":
        security_interface()

# ===== Interfaces =====
def pdf_to_images_interface():
    st.header("📄 PDF to Images Converter")
    uploaded_file = st.file_uploader("Choose PDF file", type="pdf", key="pdf_to_img")

    if uploaded_file is not None:
        col1, col2 = st.columns(2)
        with col1:
            st.info(f"File size: {len(uploaded_file.getvalue()) / 1024:.1f} KB")
            image_format = st.selectbox("Output format", ["PNG", "JPEG"])
        with col2:
            dpi = st.slider("Image quality (DPI)", 72, 300, 200)

        if st.button("Convert to Images", type="primary"):
            with st.spinner("Converting PDF to images..."):
                images = pdf_to_images_pymupdf(uploaded_file.read(), dpi=dpi, image_format=image_format)
                if images:
                    st.success(f"✅ Converted {len(images)} pages successfully!")
                    zip_buffer = io.BytesIO()
                    with zipfile.ZipFile(zip_buffer, 'w') as zip_file:
                        for i, img in enumerate(images):
                            img_buffer = io.BytesIO()
                            img.save(img_buffer, format=image_format)
                            zip_file.writestr(f"page_{i+1}.{image_format.lower()}", img_buffer.getvalue())
                    st.subheader("Preview (First Page)")
                    st.image(images[0], caption="Page 1", width=400)
                    st.download_button(
                        label="📥 Download Images (ZIP)",
                        data=zip_buffer.getvalue(),
                        file_name=f"converted_images_{image_format.lower()}.zip",
                        mime="application/zip"
                    )

def images_to_pdf_interface():
    st.header("🖼️ Images to PDF Converter")
    uploaded_files = st.file_uploader("Choose images",
        type=["png", "jpg", "jpeg", "bmp", "tiff"], accept_multiple_files=True)
    if uploaded_files:
        st.info(f"Selected {len(uploaded_files)} images")
        if st.button("Convert to PDF", type="primary"):
            with st.spinner("Creating PDF..."):
                pdf_bytes = images_to_pdf_conversion(uploaded_files)
                if pdf_bytes:
                    st.success("✅ PDF created successfully!")
                    st.download_button(
                        label="📥 Download PDF",
                        data=pdf_bytes,
                        file_name="converted_images.pdf",
                        mime="application/pdf"
                    )

def resize_images_interface():
    st.header("📏 Image Resizer")
    uploaded_file = st.file_uploader("Choose image", type=["png", "jpg", "jpeg", "bmp"])
    if uploaded_file is not None:
        img = Image.open(uploaded_file)
        orig_width, orig_height = img.size
        new_width = st.number_input("Width", value=orig_width)
        new_height = st.number_input("Height", value=orig_height)
        if st.button("Resize Image", type="primary"):
            resized_data, img_format = resize_image(uploaded_file, new_width, new_height)
            if resized_data:
                st.image(resized_data, caption=f"Resized {new_width}x{new_height}")
                st.download_button(
                    "📥 Download Resized Image",
                    data=resized_data,
                    file_name=f"resized_image.{img_format}",
                    mime=f"image/{img_format}"
                )

def compress_images_interface():
    st.header("🗜️ Image Compressor")
    uploaded_file = st.file_uploader("Choose image", type=["png", "jpg", "jpeg"])
    if uploaded_file is not None:
        quality = st.slider("Compression Quality", 10, 100, 85)
        if st.button("Compress Image", type="primary"):
            compressed_data = compress_image(uploaded_file, quality)
            if compressed_data:
                st.image(compressed_data, caption="Compressed Image")
                st.download_button(
                    "📥 Download Compressed Image",
                    data=compressed_data,
                    file_name="compressed_image.jpg",
                    mime="image/jpeg"
                )

def security_interface():
    st.header("🔒 PDF Security")
    uploaded_file = st.file_uploader("Choose PDF", type="pdf")
    if uploaded_file is not None:
        security_operation = st.selectbox("Security Operation", ["Encrypt PDF", "Decrypt PDF"])
        if security_operation == "Encrypt PDF":
            user_password = st.text_input("User Password", type="password")
            if st.button("Encrypt PDF") and user_password:
                encrypted_pdf = encrypt_pdf(uploaded_file.read(), user_password)
                if encrypted_pdf:
                    st.download_button("📥 Download Encrypted PDF", encrypted_pdf, "encrypted.pdf")
        elif security_operation == "Decrypt PDF":
            password = st.text_input("Enter Password", type="password")
            if st.button("Decrypt PDF") and password:
                decrypted_pdf = decrypt_pdf(uploaded_file.read(), password)
                if decrypted_pdf:
                    st.download_button("📥 Download Decrypted PDF", decrypted_pdf, "decrypted.pdf")

# ===== Footer =====
def show_footer():
    st.markdown("---")
    st.markdown(
        "<div style='text-align: center; color: #666; padding: 20px;'>"
        "<p>🔧 Multi-Purpose File Processor | Built with Streamlit</p>"
        "<p>Features: PDF ↔ Images • Editing • Security • Compression</p>"
        "</div>", unsafe_allow_html=True)

if __name__ == "__main__":
    main()
    show_footer()
```





