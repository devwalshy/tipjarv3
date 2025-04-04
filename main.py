import streamlit as st
import os
import base64
from mistralai import Mistral
import google.generativeai as genai
from PIL import Image
import io
import requests
import re
import math
import json
# From python-dotenv package:
from dotenv import load_dotenv

# Configure page - MUST BE THE FIRST STREAMLIT COMMAND
st.set_page_config(layout="wide", page_title="TipJar", page_icon="💰")

# Load environment variables from .env file
load_dotenv()

# Remove the extra CSS that was trying to set the background image
st.markdown("""
<style>
    /* Hide sidebar completely */
    [data-testid="stSidebar"] {
        display: none !important;
        visibility: hidden !important;
        width: 0 !important;
        margin: 0 !important;
        padding: 0 !important;
    }
    
    /* Ensure main content spans full width */
    .stApp > header + div > div {
        width: 100% !important;
    }
    
    /* Base styles for all devices */
    .stApp {
        max-width: 100%;
    }
    
    /* Mobile detection and responsive design */
    @media (max-width: 768px) {
        /* Apply mobile styles automatically based on viewport */
        .element-container {
            max-width: 95vw !important;
        }
        
        /* Improve button touch targets */
        button, [role="button"] {
            min-height: 44px !important;
            padding: 10px !important;
        }
        
        /* Better spacing for mobile UI */
        .row-widget.stRadio > div {
            flex-direction: row !important;
            margin-bottom: 10px !important;
        }
        
        /* Ensure font size is legible on mobile */
        .stTextInput input, .stNumberInput input {
            font-size: 16px !important; /* Prevents iOS zoom on focus */
        }
        
        /* Full width containers on mobile */
        .block-container, .css-18e3th9 {
            padding-left: 10px !important;
            padding-right: 10px !important;
            max-width: 95vw !important;
        }
    }
    
    /* Starbucks brand styling */
    .stButton button {
        border-radius: 20px;
        background-color: #00704A !important;
        color: white !important;
        font-weight: 500;
    }
    
    /* Custom text colors */
    h1, h2, h3 {
        color: #00704A !important;
    }
    
    /* Consistent table styling */
    table {
        width: 100%;
    }
    
    /* Container styling */
    .custom-card {
        border: 1px solid rgba(49, 51, 63, 0.2);
        border-radius: 10px;
        padding: 10px;
        margin-bottom: 10px;
    }
    
    /* iOS optimization */
    @media (max-width: 428px) { /* iPhone Pro Max width */
        /* Larger touch targets for iOS */
        button, [role="button"], .stSelectbox, .stNumberInput {
            min-height: 48px !important;
        }
        
        /* Prevent auto-zoom on inputs */
        input, select, textarea {
            font-size: 16px !important;
        }
        
        /* Full width buttons that are easier to tap */
        .stButton button {
            width: 100% !important;
            margin: 8px 0 !important;
        }
        
        /* More padding around elements */
        .block-container {
            padding: 16px !important;
        }
    }
</style>
""", unsafe_allow_html=True)

# Function to detect if we're on a mobile device (used for conditional layouts)
def is_mobile():
    # Simple width-based detection
    # We'll use a session state variable to track this
    return st.session_state.get('mobile_detected', False)

# Detect device type based on user agent or viewport
if 'mobile_detected' not in st.session_state:
    # Initialize as false - will be detected through viewport size by CSS
    st.session_state['mobile_detected'] = False

    # Add a custom component to allow users to manually toggle mobile view for testing
    # This is hidden in the UI but accessible for debugging if needed
    st.markdown("""
    <div style="display:none">
        <button onclick="
            const isMobile = window.innerWidth < 768;
            window.parent.postMessage({
                type: 'streamlit:setComponentValue',
                value: isMobile
            }, '*');
        ">Auto-detect mobile</button>
    </div>
    """, unsafe_allow_html=True)

# Title section with centered elements for all devices - simplified without image
st.markdown("""
<div style="display: flex; flex-direction: column; align-items: center; justify-content: center; margin-bottom: 0.5rem;">
    <h1 style="margin: 0; color: #00704A; text-align: center; font-size: 2.6rem;">TipJar</h1>
</div>
<div style="font-size: 1.5rem; font-style: italic; margin: 0.5rem 0 1.5rem 0; color: #00704A; text-align: center;">\"If theres a Will, Theres a Way!\" -Lauren 2025</div>
""", unsafe_allow_html=True)

# Initialize session state variables
if "ocr_result" not in st.session_state:
    st.session_state["ocr_result"] = None
if "preview_src" not in st.session_state:
    st.session_state["preview_src"] = None
if "image_bytes" not in st.session_state:
    st.session_state["image_bytes"] = None
if "tips_calculated" not in st.session_state:
    st.session_state["tips_calculated"] = False
if "week_counter" not in st.session_state:
    st.session_state["week_counter"] = 1
if "tips_history" not in st.session_state:
    st.session_state["tips_history"] = []
if "gemini_chat" not in st.session_state:
    st.session_state["gemini_chat"] = None

# Get API keys from environment variables
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# Simplified UI - only Gemini, only Image, only Local Upload
ai_provider = "Gemini"  # Set default and only option
file_type = "Image"     # Set default and only option
source_type = "Local Upload"  # Set default and only option

# Check if selected provider's API key is available
if not GEMINI_API_KEY:
    st.error("Gemini API key is not configured in the .env file. Please add it and restart the application.")
    st.stop()

# Configure Gemini with safety settings
genai.configure(api_key=GEMINI_API_KEY)
generation_config = {
    "temperature": 0.7,
    "top_p": 0.9,
    "top_k": 40,
    "max_output_tokens": 2048,
}
safety_settings = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
]

uploaded_file = st.file_uploader("Upload an Image file", type=["jpg", "jpeg", "png"])

# Process Button & OCR Handling
if st.button("Process", use_container_width=True):
    if not uploaded_file:
        st.error("Please upload an image file.")
    else:
        with st.spinner("Processing the image..."):
            try:
                # Initialize Gemini 1.5 Flash model for vision tasks
                model = genai.GenerativeModel(
                    'gemini-1.5-flash',
                    generation_config=generation_config,
                    safety_settings=safety_settings
                )
                
                # Store the original file bytes for preview
                st.session_state["image_bytes"] = uploaded_file.read()
                image = Image.open(io.BytesIO(st.session_state["image_bytes"]))
                preview_src = None
                
                # Create structured prompt for better OCR
                prompt = """Please analyze this image and:
                1. Extract all visible text, especially focusing on names and hours worked
                2. Maintain the original formatting and structure
                3. Preserve any important visual context
                4. Make sure to clearly identify all partner/employee names and their corresponding hours
                
                Extract and format the text clearly:"""
                
                response = model.generate_content([prompt, image])
                response.resolve()
                result_text = response.text
                
                # Initialize chat model for processing with Gemini 1.5 Pro
                st.session_state["gemini_chat"] = genai.GenerativeModel(
                    'gemini-1.5-pro',
                    generation_config=generation_config,
                    safety_settings=safety_settings
                ).start_chat(history=[])
                
                st.session_state["ocr_result"] = result_text
                st.session_state["preview_src"] = preview_src
                st.session_state["tips_calculated"] = False
                
            except Exception as e:
                st.error(f"Error processing with Gemini: {str(e)}")
                st.stop()

# Display Preview and OCR Result
if st.session_state["ocr_result"]:
    # Use a more mobile-friendly layout for all devices
    st.subheader("Preview")
    if st.session_state["image_bytes"]:
        st.image(st.session_state["image_bytes"], use_container_width=True)
    
    st.subheader("Extracted Tippable Hours")
    st.write(st.session_state["ocr_result"])
    
    # Extract partner data with AI assistance
    if st.button("Extract Partner Data", use_container_width=True):
        with st.spinner("Extracting partner data..."):
            try:
                prompt = f"""
                From the following text, extract partner names and their hours worked. Format as JSON:
                
                {st.session_state["ocr_result"]}
                
                Return a JSON array of objects with 'name' and 'hours' fields. Example:
                [
                    {{"name": "John Smith", "hours": 32.5}},
                    {{"name": "Jane Doe", "hours": 28.75}}
                ]
                
                Only include valid partners with hours. Output ONLY the JSON array, nothing else.
                """
                
                response = st.session_state["gemini_chat"].send_message(prompt)
                partner_data_str = response.text
                
                # Also extract the total tippable hours from the document if available
                total_hours_prompt = f"""
                From the following text, extract ONLY the total tippable hours (or total hours) mentioned in the document.
                Return ONLY the number. If you find multiple totals, return the one that's labeled as "Total Tippable Hours" or similar.
                
                {st.session_state["ocr_result"]}
                """
                
                total_hours_response = st.session_state["gemini_chat"].send_message(total_hours_prompt)
                document_total_hours_str = total_hours_response.text.strip()
                
                # Extract the JSON from the response
                pattern = r'\[\s*{.*}\s*\]'
                json_match = re.search(pattern, partner_data_str, re.DOTALL)
                
                if json_match:
                    partner_data_str = json_match.group(0)
                
                partner_data = json.loads(partner_data_str)
                
                # Add partner numbers
                for i, partner in enumerate(partner_data):
                    partner["number"] = i + 1
                
                st.session_state["partner_data"] = partner_data
                
                # Calculate total hours
                total_hours = sum(float(partner["hours"]) for partner in partner_data)
                st.session_state["total_hours"] = total_hours
                
                # Display partner data
                st.write(f"Total Hours: {total_hours}")
                st.write("Partner Data:")
                for partner in partner_data:
                    st.write(f"{partner['name']} - {partner['hours']} hours")
                
                # Compare with document's total hours if available
                try:
                    # Clean up the extracted total hours string
                    document_total_hours_str = re.sub(r'[^\d.]', '', document_total_hours_str)
                    if document_total_hours_str:
                        document_total_hours = float(document_total_hours_str)
                        st.session_state["document_total_hours"] = document_total_hours
                        
                        # Display the comparison
                        st.markdown("### Hours Validation")
                        
                        if abs(document_total_hours - total_hours) < 0.01:  # Small threshold for float comparison
                            st.success(f"✅ Validation passed! Document total ({document_total_hours}) matches calculated total ({total_hours}).")
                        else:
                            st.warning(f"⚠️ Validation check: Document shows {document_total_hours} total hours, but calculated total is {total_hours}.")
                            st.info("This discrepancy might be due to OCR errors or missing partners. Please verify manually.")
                except Exception as e:
                    st.info("Could not extract or validate total hours from the document.")
                
            except Exception as e:
                st.error(f"Error extracting partner data: {str(e)}")
                st.error("Please try again or manually enter partner data.")
    
    # Manual Partner Data Entry Option - make more iOS-friendly
    with st.expander("Or Manually Enter Partner Data"):
        num_partners = st.number_input("Number of Partners", min_value=1, max_value=20, value=3)
        manual_partner_data = []
        
        # Use vertical stacking for all devices for easier touch input
        for i in range(num_partners):
            with st.container():
                st.markdown(f"<h4 style='margin-bottom: 0px; color: #00704A;'>Partner {i+1}</h4>", unsafe_allow_html=True)
                name = st.text_input(f"Name", key=f"name_{i}")
                hours = st.number_input(f"Hours", min_value=0.0, step=0.25, key=f"hours_{i}")
            
            if name:  # Only add if name is provided
                manual_partner_data.append({"name": name, "number": i+1, "hours": hours})
        
        if st.button("Save Partner Data", use_container_width=True):
            if all(partner["name"] for partner in manual_partner_data):
                st.session_state["partner_data"] = manual_partner_data
                st.session_state["total_hours"] = sum(float(partner["hours"]) for partner in manual_partner_data)
                st.success("Partner data saved successfully!")
            else:
                st.error("Please provide names for all partners.")
    
    # Tip Allocation Section
    if "partner_data" in st.session_state and not st.session_state["tips_calculated"]:
        total_tip_amount = st.number_input("Enter total tip amount for the week: $", min_value=0.0, step=10.0)
        
        if st.button("Calculate Tips", use_container_width=True):
            if total_tip_amount > 0:
                # Process Week Counter
                if "week_counter" not in st.session_state:
                    st.session_state["week_counter"] = 1
                
                # Calculate individual tips
                partner_data = st.session_state["partner_data"]
                total_hours = st.session_state["total_hours"]
                
                # Calculate hourly tip rate - DO NOT round this
                hourly_rate = total_tip_amount / total_hours
                
                # Truncate to hundredths place (e.g., 1.618273 becomes 1.61)
                hourly_rate = int(hourly_rate * 100) / 100
                
                for partner in partner_data:
                    # Calculate exact tip amount (hours * hourly_rate)
                    exact_amount = float(partner["hours"]) * hourly_rate
                    
                    # Store the exact unrounded amount
                    partner["raw_tip_amount"] = exact_amount
                    
                    # Store the unrounded amount for display purposes
                    partner["exact_tip_amount"] = exact_amount
                    
                    # Round directly to nearest dollar for cash distribution (e.g., $43.1725 → $43)
                    partner["tip_amount"] = round(exact_amount)
                
                # Add information about the hourly rate and rounding policy
                st.info(f"""
                **Hourly Rate**: ${hourly_rate:.2f} per hour
                """)
                
                # Distribute bills
                denominations = [20, 10, 5, 1]
                
                # Determine starting partner index based on rotation
                num_partners = len(partner_data)
                start_index = (st.session_state["week_counter"] - 1) % num_partners
                
                # Process each partner's distribution
                remaining_amounts = {}
                for partner in partner_data:
                    remaining_amounts[partner["number"]] = partner["tip_amount"]
                
                # Initialize bill counts for each partner
                for partner in partner_data:
                    partner["bills"] = {20: 0, 10: 0, 5: 0, 1: 0}
                
                # Distribute by denomination, starting with largest
                for denomination in denominations:
                    # Create an order of partners, starting with the rotation partner
                    partner_order = [(start_index + i) % num_partners for i in range(num_partners)]
                    
                    # Keep distributing bills of this denomination while possible
                    while True:
                        distributed = False
                        for idx in partner_order:
                            partner_num = partner_data[idx]["number"]
                            if remaining_amounts[partner_num] >= denomination:
                                # Give this partner a bill of this denomination
                                partner_data[idx]["bills"][denomination] += 1
                                remaining_amounts[partner_num] -= denomination
                                distributed = True
                        
                        # If we couldn't distribute any more of this denomination, move to next
                        if not distributed:
                            break
                
                # Add the bill distribution to each partner's data
                for partner in partner_data:
                    bills_text = []
                    for denom in [20, 10, 5, 1]:
                        if partner["bills"][denom] > 0:
                            bills_text.append(f"{partner['bills'][denom]}x${denom}")
                    
                    partner["bills_text"] = ",".join(bills_text)
                    
                    # Format for copy-paste
                    partner["formatted_output"] = (
                        f"Partner Name: {partner['name']} | #: {partner['number']} | "
                        f"Hours: {partner['hours']} | Exact: ${partner['exact_tip_amount']:.2f} | "
                        f"Cash: ${partner['tip_amount']} | Bills: {partner['bills_text']}"
                    )
                
                # Save to session state
                st.session_state["distributed_tips"] = partner_data
                st.session_state["total_tip_amount"] = total_tip_amount
                st.session_state["hourly_rate"] = hourly_rate
                st.session_state["tips_calculated"] = True
                
                # Increment week counter for the next allocation
                st.session_state["week_counter"] += 1
            else:
                st.error("Please enter a valid tip amount.")
    
    # Display Tip Distribution Results
    if st.session_state.get("tips_calculated", False):
        st.subheader("Tip Distribution Results")
        
        # Display the hourly rate and calculation
        total_tip_amount = st.session_state['total_tip_amount']
        total_hours = st.session_state['total_hours']
        hourly_rate = st.session_state['hourly_rate']
        
        st.markdown(f"""
        <div style="background-color: #262730; padding: 12px; border-radius: 8px; margin-bottom: 15px; color: white;">
            <p style="margin: 0"><strong>Calculation:</strong></p>
            <p style="margin: 0">Total Tips: ${total_tip_amount:.2f} ÷ Total Hours: {total_hours:.2f} = <strong>${hourly_rate:.2f}</strong> per hour</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Prepare tip data with calculations shown
        tip_data = []
        for partner in st.session_state["distributed_tips"]:
            exact_amount = partner['exact_tip_amount']
            calculation = f"{partner['hours']} × ${hourly_rate:.2f} = ${exact_amount:.2f}"
            
            tip_data.append({
                "Partner Name": partner["name"],
                "#": partner["number"],
                "Hours": partner["hours"],
                "Calculation": calculation,
                "Cash Amount": f"${partner['tip_amount']}",
                "Bills": partner["bills_text"]
            })
        
        # Use card-based layout with compact design for all devices
        for partner in tip_data:
            with st.container():
                st.markdown(f"""
                <div class="custom-card" style="padding: 8px; margin-bottom: 8px;">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <h4 style="margin: 0; color: #00704A; font-size: 16px;">{partner['Partner Name']} <span style="color: #666; font-size: 14px;">#{partner['#']}</span></h4>
                        <span style="color: #00704A; font-weight: bold; font-size: 16px;">{partner['Cash Amount']}</span>
                    </div>
                    <div style="font-size: 13px; margin-top: 4px;">
                        <span>{partner['Hours']} hours</span>
                    </div>
                    <div style="font-size: 12px; margin-top: 2px; color: #666;">
                        {partner['Calculation']} → {partner['Cash Amount']}
                    </div>
                    <div style="font-size: 12px; margin-top: 2px;">
                        <small>Bills: {partner['Bills']}</small>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        
        # Display copy-paste ready format
        with st.expander("Copy-paste format"):
            for partner in st.session_state["distributed_tips"]:
                st.text(partner["formatted_output"])
        
        # Save distribution to history
        if st.button("Save to History", use_container_width=True):
            distribution = {
                "week": st.session_state["week_counter"] - 1,
                "total_amount": st.session_state["total_tip_amount"],
                "total_hours": st.session_state["total_hours"],
                "partners": st.session_state["distributed_tips"]
            }
            
            if "tips_history" not in st.session_state:
                st.session_state["tips_history"] = []
            
            st.session_state["tips_history"].append(distribution)
            st.success("Distribution saved to history!")
    
    # History section - simplified for mobile
    if "tips_history" in st.session_state and st.session_state["tips_history"]:
        with st.expander("View Distribution History"):
            for i, dist in enumerate(st.session_state["tips_history"]):
                with st.container():
                    st.markdown(f"""
                    <div class="custom-card">
                        <h4 style="margin: 0; color: #00704A;">Week {dist['week']}</h4>
                        <p>Total: ${dist['total_amount']} for {dist['total_hours']} hours</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    for partner in dist["partners"]:
                        st.markdown(f"""
                        <div style="padding-left: 15px; margin-bottom: 5px;">
                            {partner['name']} | #{partner['number']} | {partner['hours']} hours | ${partner['tip_amount']} | {partner['bills_text']}
                        </div>
                        """, unsafe_allow_html=True)
                    
                    st.markdown("<hr style='margin: 15px 0;'>", unsafe_allow_html=True)
    
    # Download options for OCR result - more touch-friendly
    if st.session_state.get("tips_calculated", False):
        # Generate HTML table for download
        def generate_html_table(tip_data):
            html = """
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>TipJar Results</title>
                <style>
                    body {
                        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
                        margin: 20px;
                        padding: 0;
                        color: #333;
                    }
                    h1 {
                        color: #00704A;
                        text-align: center;
                    }
                    .info {
                        margin: 10px 0;
                        background-color: #f8f9fa;
                        padding: 10px;
                        border-radius: 8px;
                    }
                    table {
                        width: 100%;
                        border-collapse: collapse;
                        margin-top: 20px;
                        border-radius: 8px;
                        overflow: hidden;
                    }
                    th, td {
                        border: 1px solid #ddd;
                        padding: 12px 8px;
                        text-align: left;
                    }
                    th {
                        background-color: #00704A;
                        color: white;
                    }
                    tr:nth-child(even) {
                        background-color: #f2f2f2;
                    }
                    .calculation {
                        color: #666;
                        font-size: 0.9em;
                    }
                    .cash-amount {
                        font-weight: bold;
                        color: #00704A;
                    }
                    @media (max-width: 600px) {
                        th, td {
                            padding: 8px 4px;
                            font-size: 14px;
                        }
                    }
                </style>
            </head>
            <body>
                <h1>Tip Distribution Results</h1>
                <div class="info">
                    <p><strong>Hourly Rate Calculation:</strong> $""" + f"{total_tip_amount:.2f} ÷ {total_hours:.2f} = ${hourly_rate:.2f}" + """ per hour</p>
                </div>
                <table>
                    <thead>
                        <tr>
                            <th>#</th>
                            <th>Partner Name</th>
                            <th>Hours</th>
                            <th>Calculation</th>
                            <th>Cash</th>
                            <th>Bills</th>
                        </tr>
                    </thead>
                    <tbody>
            """
            
            for partner in tip_data:
                html += f"""
                        <tr>
                            <td>{partner['#']}</td>
                            <td>{partner['Partner Name']}</td>
                            <td>{partner['Hours']}</td>
                            <td class="calculation">{partner['Calculation']}</td>
                            <td class="cash-amount">{partner['Cash Amount']}</td>
                            <td>{partner['Bills']}</td>
                        </tr>
                """
            
            html += """
                    </tbody>
                </table>
            </body>
            </html>
            """
            
            return html
        
        # Get the tip distribution data to create HTML table
        html_content = generate_html_table(tip_data)
        html_b64 = base64.b64encode(html_content.encode()).decode()
        
        # Display download options - stacked for better mobile/touch experience
        st.subheader("Download Options")
        
        # Download original OCR text
        b64 = base64.b64encode(st.session_state["ocr_result"].encode()).decode()
        href_ocr = f'<div style="margin: 10px 0;"><a href="data:file/txt;base64,{b64}" download="ocr_result.txt" class="stButton" style="text-decoration: none;"><button style="width: 100%; border-radius: 20px; background-color: #00704A; color: white; padding: 12px; border: none; font-weight: 500;">Download OCR Text</button></a></div>'
        st.markdown(href_ocr, unsafe_allow_html=True)
        
        # Download formatted HTML table
        html_href = f'<div style="margin: 10px 0;"><a href="data:text/html;base64,{html_b64}" download="tip_distribution.html" class="stButton" style="text-decoration: none;"><button style="width: 100%; border-radius: 20px; background-color: #00704A; color: white; padding: 12px; border: none; font-weight: 500;">Download as Table</button></a></div>'
        st.markdown(html_href, unsafe_allow_html=True)
    
    elif st.session_state.get("ocr_result"):
        # Just provide the OCR text download if tips haven't been calculated
        st.subheader("Download Options")
        b64 = base64.b64encode(st.session_state["ocr_result"].encode()).decode()
        href = f'<div style="margin: 10px 0;"><a href="data:file/txt;base64,{b64}" download="ocr_result.txt" class="stButton" style="text-decoration: none;"><button style="width: 100%; border-radius: 20px; background-color: #00704A; color: white; padding: 12px; border: none; font-weight: 500;">Download OCR Result</button></a></div>'
        st.markdown(href, unsafe_allow_html=True)

# Add Starbucks-themed footer - updated as requested
st.markdown("---")
st.markdown(
    """
    <div style="text-align: center; color: #00704A; margin-top: 20px;">
        <p style="margin-bottom: 0;">Made by William Walsh</p>
        <p style="margin-top: 2px;">Starbucks Store# 69600</p>
    </div>
    """, 
    unsafe_allow_html=True
) 