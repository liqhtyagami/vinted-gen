 - @light, @zkjaimport streamlit as st
import sqlite3
import os
import tempfile
from sold_generator_pixel_perfect import measure_reference, generate_sold_image, TEMPLATE_PATH, REFERENCE_PATH, OUT_PATH

st.set_page_config(page_title="Fake Vinted Sold Listing Generator - @light, @zkja", layout="centered")

def check_license(license_key):
    conn = sqlite3.connect("licenses.db")
    c = conn.cursor()
    c.execute("SELECT username FROM licenses WHERE license_key = ?", (license_key,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else None

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = None

# Store last generated image in session so it persists
if "last_image_path" not in st.session_state:
    st.session_state.last_image_path = None

st.title("V-Com Vinted Generator - @light, @zkja")

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

if st.session_state.logged_in:
    st.title("Fake Vinted Sold Listing Generator")
    st.write(f"Logged in as: **{st.session_state.username}**")

    product_file = st.file_uploader("Upload product photo", type=["png", "jpg", "jpeg"])

    # --- Main product details form ---
    with st.form("sold_form"):
        title_text = st.text_input("Product Title", placeholder="Van Cleef & Arpels Bracelet")
        condition_text = st.text_input("Condition", placeholder="Very good")
        brand_text = st.text_input("Brand", placeholder="Van Cleef & Arpels")
        price_text = st.text_input("Price", placeholder="400.00")
        total_text = st.text_input("Total incl. Buyer Protection", placeholder="420.70")
        currency_choice = st.radio("Currency", ["GBP", "USD"], horizontal=True)

        submitted_sold = st.form_submit_button("Generate Image")

    # --- Live extra text UI ---
    if "add_extra_text" not in st.session_state:
        st.session_state.add_extra_text = False
    if "extra_text1" not in st.session_state:
        st.session_state.extra_text1 = ""
    if "extra_text2" not in st.session_state:
        st.session_state.extra_text2 = ""
    if "extra_text3" not in st.session_state:
        st.session_state.extra_text3 = ""
    if "extra_size" not in st.session_state:
        st.session_state.extra_size = 75  # default now 75
    if "extra_stroke" not in st.session_state:
        st.session_state.extra_stroke = 4  # default now 4

    st.checkbox("Add Extra Text Overlay", key="add_extra_text")

    extra_text_lines, extra_text_size, extra_text_stroke = None, 75, 4
    if st.session_state.add_extra_text:
        text1 = st.text_input("Text 1", placeholder="Paid: $5", key="extra_text1")
        text2 = st.text_input("Text 2", placeholder="Sold: $10", key="extra_text2")
        text3 = st.text_input("Text 3", placeholder="Profit: $5", key="extra_text3")
        extra_text_lines = [text1, text2, text3]
        extra_text_size = st.slider("Text Size", 10, 150, st.session_state.extra_size, key="extra_size")
        extra_text_stroke = st.slider("Stroke Width", 0, 10, st.session_state.extra_stroke, key="extra_stroke")

    # --- Generate image ---
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
                    currency=currency_choice,
                    extra_text_lines=extra_text_lines if st.session_state.add_extra_text else None,
                    extra_text_size=extra_text_size,
                    extra_text_stroke=extra_text_stroke
                )

                result_img.save(OUT_PATH)
                st.session_state.last_image_path = OUT_PATH  # Save path in session
                st.image(result_img, caption="Generated Sold Listing", use_container_width=True)
                with open(OUT_PATH, "rb") as f:
                    st.download_button(
                        label="Download Image",
                        data=f,
                        file_name="sold_image.png",
                        mime="image/png"
                    )

    # --- Display last generated image if exists ---
    if st.session_state.last_image_path and not submitted_sold:
        if os.path.exists(st.session_state.last_image_path):
            st.image(st.session_state.last_image_path, caption="Previously Generated Image", use_container_width=True)

else:
    st.info("Please enter your license key to login.")


