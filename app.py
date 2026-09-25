
import streamlit as st
import sqlite3
import hashlib
import qrcode
from io import BytesIO
import cv2
import numpy as np

# --- DATABASE SETUP ---
def init_db():
    conn = sqlite3.connect('results.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS student_results (
            id TEXT PRIMARY KEY,
            name TEXT,
            course TEXT,
            grade TEXT,
            result_hash TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# --- APP LAYOUT (Forced to One Line) ---
st.markdown(
    "<h1 style='font-size: 24px; white-space: nowrap;'>🎓 QR Code Result Verification System</h1>", 
    unsafe_allow_html=True
)

menu = st.sidebar.selectbox("Navigation Menu", ["Admin Portal", "Result Verification Portal"])

# --- SESSION STATE FOR LOGIN ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

# ==========================================
# 1. ADMIN PORTAL
# ==========================================
if menu == "Admin Portal":
    st.header("🔐 Admin Portal")
    
    # If NOT logged in, show the Login Form with a button
    if not st.session_state.logged_in:
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            login_submit = st.form_submit_button(label="Login")
            
            if login_submit:
                if username == "admin" and password == "1234":
                    st.session_state.logged_in = True
                    st.success("Login Successful!")
                    st.rerun()
                else:
                    st.error("Invalid Username or Password (Try admin / 1234)")
                    
    # If ALREADY logged in, show the Result Generation Dashboard & Logout button
    else:
        st.success("✅ You are logged in as Administrator.")
        if st.button("Logout"):
            st.session_state.logged_in = False
            st.rerun()
            
        st.divider()
        st.subheader("Step 2: Enter Student Details")
        with st.form("result_form"):
            student_id = st.text_input("Student ID (e.g., CSC/2026/001)")
            name = st.text_input("Full Name")
            course = st.text_input("Course Code (e.g., MTH101)")
            grade = st.selectbox("Grade", ["A", "B", "C", "D", "E", "F"])
            
            submit_button = st.form_submit_button(label="Generate Secure Hash & QR Code")
            
            if submit_button:
                if student_id and name and course:
                    # Step 3a: Hashing data
                    raw_data = f"ID:{student_id}|Name:{name}|Course:{course}|Grade:{grade}"
                    secure_hash = hashlib.sha256(raw_data.encode()).hexdigest()
                    
                    # Save to database
                    conn = sqlite3.connect('results.db')
                    cursor = conn.cursor()
                    try:
                        cursor.execute("INSERT INTO student_results (id, name, course, grade, result_hash) VALUES (?, ?, ?, ?, ?)",
                                       (student_id, name, course, grade, secure_hash))
                        conn.commit()
                    except sqlite3.IntegrityError:
                        cursor.execute("UPDATE student_results SET name=?, course=?, grade=?, result_hash=? WHERE id=?",
                                       (name, course, grade, secure_hash, student_id))
                        conn.commit()
                    conn.close()
                    
                    st.success("Result registered and secured successfully!")
                    
                    # Display hash with a built-in COPY button
                    st.write("📋 **Generated Hash Code (Click copy icon top right):**")
                    st.code(secure_hash, language="text")
                    
                    # Step 3b: Generate QR code image display
                    img = qrcode.make(secure_hash)
                    buffered = BytesIO()
                    img.save(buffered, format="PNG")
                    
                    st.image(buffered.getvalue(), caption=f"QR Code for {name}", width=250)
                else:
                    st.warning("Please fill in all the required fields.")

# ==========================================
# 2. VERIFICATION PORTAL
# ==========================================
elif menu == "Result Verification Portal":
    st.header("📱 Result Verification Scanner")
    st.write("Verify the authenticity of a student result.")
    
    # Choose verification method
    method = st.radio("Choose Verification Method:", ["Paste Hash Code", "Upload QR Code Image"])
    
    scanned_hash = ""
    
    if method == "Paste Hash Code":
        scanned_hash = st.text_input("Paste the copied hash code here:")
        
    elif method == "Upload QR Code Image":
        uploaded_file = st.file_uploader("Upload the QR Code image (.png or .jpg)", type=["png", "jpg", "jpeg"])
        
        if uploaded_file is not None:
            file_bytes = np.asarray(bytearray(uploaded_file.read()), dtype=np.uint8)
            opencv_image = cv2.imdecode(file_bytes, 1)
            
            detector = cv2.QRCodeDetector()
            data, bbox, straight_qrcode = detector.detectAndDecode(opencv_image)
            
            if data:
                scanned_hash = data
                st.success("✅ QR Code successfully scanned from image!")
                st.info(f"Extracted Hash: `{scanned_hash}`")
            else:
                st.error("❌ Could not read a valid QR code from this image. Try uploading a clearer picture.")

    # Verification execution button
    if st.button("Verify Result"):
        if scanned_hash:
            conn = sqlite3.connect('results.db')
            cursor = conn.cursor()
            cursor.execute("SELECT name, course, grade FROM student_results WHERE result_hash = ?", (scanned_hash.strip(),))
            record = cursor.fetchone()
            conn.close()
            
            if record:
                st.balloons()
                st.success("🎉 VERIFICATION SUCCESSFUL: Authentic Result Found!")
                st.write(f"**Student Name:** {record[0]}")
                st.write(f"**Course Code:** {record[1]}")
                st.write(f"**Grade Awarded:** {record[2]}")
            else:
                st.error("🚨 WARNING: Verification Failed! This Hash/QR Code is Fake or Modified.")
        else:
            st.warning("Please provide a valid hash or image first.")
