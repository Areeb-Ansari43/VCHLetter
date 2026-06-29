import streamlit as st
import os
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor

# --- PDF Generation Logic ---
def generate_pdf(data):
    output_filename = "Generated_Permission_Letter.pdf"
    c = canvas.Canvas(output_filename, pagesize=letter)
    width, height = letter

    # Background
    if os.path.exists("image_f4efbe.png"):
        c.drawImage("image_f4efbe.png", 0, 0, width=width, height=height)

    # Date
    c.setFont("Helvetica", 11)
    c.drawRightString(width - 54, 595, data["date"])

    # Title & Salutation
    c.setFont("Helvetica-Bold", 22)
    c.drawCentredString(width / 2, 550, "PERMISSION LETTER")
    c.setFont("Helvetica", 11)
    c.drawString(54, 520, "To Whom It May Concern,")

    # Body
    c.drawString(54, 490, "We confirm that the below vehicle can be used for the carriage of passengers for hire and reward by prior")
    c.drawString(54, 475, "appointments (private hire) as specified on insurance policy :")
    c.setFont("Helvetica-Bold", 11)
    c.drawString(402, 475, data["insurance_policy"])
    
    c.setFont("Helvetica", 11)
    c.drawString(54, 460, "We authorise and give permission to the following individual to use the vehicle for all private hire bookings")
    c.drawString(54, 445, "from UBER, BOLT, OLA , FREE NOW app , WHEELY and other private hire operators.")

    # Driver & Vehicle Fields
    fields = [
        ("Vehicle Registration", data["registration"]),
        ("Make and Model", data["make_model"]),
        ("Driver Name", data["driver_name"]),
        ("Address", data["address"]),
        ("Driving Licence No", data["license_no"]),
    ]
    for i, (label, val) in enumerate(fields):
        y = 405 - (i * 22)
        c.setFont("Helvetica", 11)
        c.drawString(54, y, f"{label} :")
        c.drawString(180, y, val)

    # Hire Dates
    c.drawString(54, 275, "Hire start date.")
    c.drawString(145, 275, ":")
    c.drawString(160, 275, data["start_date"])
    c.drawString(54, 260, "Hire end date")
    c.drawString(145, 260, ":")
    c.drawString(160, 260, data["end_date"])

    # Sign-off
    c.drawString(54, 220, "Regards,")
    if os.path.exists("signature.png"):
        c.drawImage("signature.png", 54, 180, width=70, height=35, mask='auto')
    c.drawString(54, 160, "Muhammad Sohail Qureshi")
    c.drawString(54, 145, "Director(FA-IBI LTD)")

    c.save()
    return output_filename

# --- Web Interface Logic ---
st.title("FA-IBI Letter Generator")
st.write("Fill out the fields below to instantly generate a 1:1 replica PDF.")

with st.form("letter_form"):
    col1, col2 = st.columns(2)
    with col1:
        date = st.text_input("Document Date", "29/06/2026")
        insurance = st.text_input("Insurance Policy No", "HAVFL-000211")
        reg = st.text_input("Vehicle Registration")
        model = st.text_input("Make and Model")
    with col2:
        name = st.text_input("Driver Name")
        licence = st.text_input("Driving Licence No")
        start = st.text_input("Hire Start Date")
        end = st.text_input("Hire End Date")
        
    address = st.text_area("Driver Address")
    submitted = st.form_submit_button("Generate PDF")

if submitted:
    payload = {
        "date": date, "insurance_policy": insurance, "registration": reg,
        "make_model": model, "driver_name": name, "address": address,
        "license_no": licence, "start_date": start, "end_date": end
    }
    pdf_path = generate_pdf(payload)
    with open(pdf_path, "rb") as file:
        st.download_button(label="Download Completed PDF", data=file, file_name="Permission_Letter.pdf", mime="application/pdf")
