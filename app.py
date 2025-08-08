import streamlit as st
import sqlite3
from PIL import Image
import os
import tempfile
from sold_generator_pixel_perfect import measure_reference, generate_sold_image, TEMPLATE_PATH, REFERENCE_PATH, FONT_REGULAR_PATH, FONT_MEDIUM_PATH, OUT_PATH




st.set_page_config(page_title="Fake Vinted Sold Listing Generator", layout="centered")

# --- DB helper function ---
def check_license(license_key):
    conn = sqlite3.connect("licenses.db")
    c = conn.cursor()
    c.execute("SELECT username FROM licenses WHERE license_key = ?", (license_key,))
    row = c.fetchone()
    conn.close()
    if row:
        return row[0]  # username
    return None

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = None

st.title("🔐 Login with License Key")

with st.form("login_form"):
    license_key_input = st.text_input("License Key", type="password")
    submitted = st.form_submit_button("Login")

if submitted:
    username = check_license(license_key_input.strip())
    if username:
        st.success(f"Access granted! Welcome, {username}.")
        st.session_state.logged_in = True
        st.session_state.username = username
    else:
        st.error("Invalid license key.")
        st.session_state.logged_in = False
        st.session_state.username = None

if st.session_state.logged_in:
    st.title("📦 Fake Vinted Sold Listing Generator")
    st.write(f"Logged in as: **{st.session_state.username}**")
    st.write("Generate pixel-perfect fake Vinted 'Sold' listings. Measurements and layout are exactly preserved.")

    # Product image upload
    product_file = st.file_uploader("Upload product photo", type=["png", "jpg", "jpeg"])

    # Form inputs
    with st.form("sold_form"):
        title_text = st.text_input("Product Title", "Van Cleef & Arpels Malachite Vintage Alhambra 5 Motif Bracelet.")
        condition_text = st.text_input("Condition", "Very good")
        brand_text = st.text_input("Brand", "Van Cleef & Arpels")
        price_text = st.text_input("Price (e.g. 400.00)", "400.00")
        total_text = st.text_input("Total incl. Buyer Protection", "420.70")
        submitted_sold = st.form_submit_button("Generate Image")

    if submitted_sold:
        if not product_file:
            st.error("Please upload a product image.")
        else:
            with tempfile.TemporaryDirectory() as tmpdir:
                product_path = os.path.join(tmpdir, "product.png")
                with open(product_path, "wb") as f:
                    f.write(product_file.read())

                measurements = measure_reference(REFERENCE_PATH)

                result_img = generate_sold_image(
                    TEMPLATE_PATH,
                    measurements,
                    product_path,
                    title=title_text,
                    condition=condition_text,
                    brand=brand_text,
                    price=price_text,
                    total=total_text,
                )

                result_img.save(OUT_PATH)

                st.image(result_img, caption="Generated Sold Listing", use_container_width=True)
                with open(OUT_PATH, "rb") as f:
                    st.download_button(
                        label="Download Image",
                        data=f,
                        file_name="sold_image.png",
                        mime="image/png"
                    )
else:
    st.info("Please enter your license key to login.")
