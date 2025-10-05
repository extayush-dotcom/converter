import streamlit as st
from PIL import Image
import img2pdf
import io
import zipfile
import pytesseract
import cv2
import numpy as np
import fitz  # PyMuPDF
from pypdf import PdfReader, PdfWriter
import pikepdf
import base64
import os
import tempfile
import easyocr

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

# Helper Functions
def create_download_link(data, filename, text="Download"):
    b64 = base64.b64encode(data).decode()
    href = f'<a href="data:application/octet-stream;base64,{b64}" download="{filename}">{text}</a>'
    return href

# ===== PDF to Image with PyMuPDF (No Poppler) =====
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

# ===== OCR =====
def perform_ocr_on_pdf(pdf_file, language='eng'):
    """Extract text from PDF using EasyOCR (PyMuPDF + EasyOCR)"""
    try:
        pdf_file.seek(0)
        pdf_bytes = pdf_file.read()
        images = pdf_to_images_pymupdf(pdf_bytes)

        lang_map = {
            'eng': 'en', 'spa': 'es', 'fra': 'fr', 'deu': 'de',
            'hin': 'hi', 'chi_sim': 'ch_sim'
        }
        easyocr_lang = lang_map.get(language, 'en')
        reader = easyocr.Reader([easyocr_lang], gpu=False)

        extracted_text = []
        progress_bar = st.progress(0)
        status_text = st.empty()

        for page_num, page in enumerate(images):
            status_text.text(f'Processing page {page_num + 1} of {len(images)}...')
            img_array = np.array(page)
            results = reader.readtext(img_array, detail=0)
            text = "\n".join(results)
            extracted_text.append(f"--- Page {page_num + 1} ---\n{text}\n")
            progress_bar.progress((page_num + 1) / len(images))

        status_text.text('OCR completed!')
        return extracted_text
    except Exception as e:
        st.error(f"OCR Error: {e}")
        return None

def perform_ocr_on_image(image_file, language='eng'):
    lang_map = {
        'eng': 'en', 'spa': 'es', 'fra': 'fr', 
        'deu': 'de', 'hin': 'hi', 'chi_sim': 'ch_sim'
    }
    easyocr_lang = lang_map.get(language, 'en')
    reader = easyocr.Reader([easyocr_lang], gpu=False)
    img = Image.open(image_file)
    img_array = np.array(img)
    results = reader.readtext(img_array, detail=0)
    return "\n".join(results)

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

def images_to_pdf_conversion(image_files):
    try:
        img_data = []
        for img_file in image_files:
            img_file.seek(0)
            img_data.append(img_file.read())
        pdf_bytes = img2pdf.convert(img_data)
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
         "🗜️ Compress Images", "📖 OCR Text Extraction", "🔒 PDF Security"]
    )

    if operation == "📄 PDF to Images":
        pdf_to_images_interface()
    elif operation == "🖼️ Images to PDF":
        images_to_pdf_interface()
    elif operation == "📏 Resize Images":
        resize_images_interface()
    elif operation == "🗜️ Compress Images":
        compress_images_interface()
    elif operation == "📖 OCR Text Extraction":
        ocr_interface()
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

def ocr_interface():
    st.header("📖 OCR Text Extraction")
    uploaded_file = st.file_uploader("Choose PDF or Image", type=["pdf", "png", "jpg", "jpeg"])
    if uploaded_file is not None:
        language = st.selectbox("OCR Language", 
            {'English': 'eng', 'Spanish': 'spa', 'French': 'fra',
             'German': 'deu', 'Hindi': 'hin', 'Chinese': 'chi_sim'}.items(),
            format_func=lambda x: x[0])
        language_code = language[1]
        if st.button("Extract Text", type="primary"):
            if uploaded_file.type == "application/pdf":
                extracted_text = perform_ocr_on_pdf(uploaded_file, language_code)
                if extracted_text:
                    full_text = "\n".join(extracted_text)
                    st.text_area("Extracted Text", full_text, height=400)
            else:
                text = perform_ocr_on_image(uploaded_file, language_code)
                st.text_area("Extracted Text", text, height=300)

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
        "<p>Features: PDF ↔ Images • OCR • Editing • Security • Compression</p>"
        "</div>", unsafe_allow_html=True)

if __name__ == "__main__":
    main()
    show_footer()

