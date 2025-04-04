import os
import base64
import json
import re
import math
import io
from PIL import Image
import requests
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from werkzeug.utils import secure_filename
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
app.secret_key = os.urandom(24)  # For session management
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg'}

# Create uploads folder if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Get API keys from environment variables
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# Check if Gemini API key is available
if not GEMINI_API_KEY:
    print("Warning: Gemini API key is not configured in the .env file.")

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

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

@app.route('/')
def index():
    # Initialize session variables if they don't exist
    if 'week_counter' not in session:
        session['week_counter'] = 1
    if 'tips_history' not in session:
        session['tips_history'] = []
    
    return render_template('index.html')

@app.route('/process_image', methods=['POST'])
def process_image():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    if file and allowed_file(file.filename):
        try:
            # Save the file
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            # Store filepath in session
            session['image_path'] = filepath
            
            # Initialize Gemini model for vision tasks
            model = genai.GenerativeModel(
                'gemini-1.5-flash',
                generation_config=generation_config,
                safety_settings=safety_settings
            )
            
            # Open image for processing
            image = Image.open(filepath)
            
            # Create structured prompt for better OCR
            prompt = """Please analyze this image and:
            1. Extract all visible text, especially focusing on names and hours worked
            2. Maintain the original formatting and structure
            3. Preserve any important visual context
            4. Make sure to clearly identify all partner/employee names and their corresponding hours
            
            Extract and format the text clearly:"""
            
            # Process with Gemini
            response = model.generate_content([prompt, image])
            response.resolve()
            result_text = response.text
            
            # Initialize chat model for further processing
            gemini_chat = genai.GenerativeModel(
                'gemini-1.5-pro',
                generation_config=generation_config,
                safety_settings=safety_settings
            ).start_chat(history=[])
            
            # Store chat session for later use (convert to list for serialization)
            session['gemini_chat_history'] = []
            session['ocr_result'] = result_text
            
            return jsonify({
                'success': True, 
                'ocr_result': result_text,
                'image_path': '/'.join(filepath.split(os.sep)[-2:])  # Return relative path
            })
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    return jsonify({'error': 'File type not allowed'}), 400

@app.route('/extract_partner_data', methods=['POST'])
def extract_partner_data():
    if 'ocr_result' not in session:
        return jsonify({'error': 'No OCR result available'}), 400
    
    try:
        # Initialize Gemini model for text processing
        model = genai.GenerativeModel(
            'gemini-1.5-pro',
            generation_config=generation_config,
            safety_settings=safety_settings
        )
        
        # Create prompt for partner data extraction
        prompt = f"""
        From the following text, extract partner names and their hours worked. Format as JSON:
        
        {session['ocr_result']}
        
        Return a JSON array of objects with 'name' and 'hours' fields. Example:
        [
            {{"name": "John Smith", "hours": 32.5}},
            {{"name": "Jane Doe", "hours": 28.75}}
        ]
        
        Only include valid partners with hours. Output ONLY the JSON array, nothing else.
        """
        
        # Process with Gemini
        response = model.generate_content(prompt)
        partner_data_str = response.text
        
        # Extract the JSON from the response
        pattern = r'\[\s*{.*}\s*\]'
        json_match = re.search(pattern, partner_data_str, re.DOTALL)
        
        if json_match:
            partner_data_str = json_match.group(0)
        
        partner_data = json.loads(partner_data_str)
        
        # Add partner numbers
        for i, partner in enumerate(partner_data):
            partner["number"] = i + 1
        
        # Calculate total hours
        total_hours = sum(float(partner["hours"]) for partner in partner_data)
        
        # Store in session
        session['partner_data'] = partner_data
        session['total_hours'] = total_hours
        
        return jsonify({
            'success': True, 
            'partner_data': partner_data,
            'total_hours': total_hours
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/calculate_tips', methods=['POST'])
def calculate_tips():
    if 'partner_data' not in session:
        return jsonify({'error': 'No partner data available'}), 400
    
    try:
        # Get total tip amount from request
        data = request.get_json()
        total_tip_amount = float(data.get('totalTipAmount', 0))
        
        if total_tip_amount <= 0:
            return jsonify({'error': 'Please enter a valid tip amount'}), 400
        
        # Get partner data and total hours from session
        partner_data = session['partner_data']
        total_hours = session['total_hours']
        
        # Calculate hourly tip rate - DO NOT round this
        hourly_rate = total_tip_amount / total_hours
        
        # Truncate to hundredths place (e.g., 1.618273 becomes 1.61)
        hourly_rate = int(hourly_rate * 100) / 100
        
        # Calculate individual tips
        for partner in partner_data:
            # Calculate exact tip amount (hours * hourly_rate)
            exact_amount = float(partner["hours"]) * hourly_rate
            
            # Store the exact unrounded amount
            partner["raw_tip_amount"] = exact_amount
            
            # Store the unrounded amount for display purposes
            partner["exact_tip_amount"] = exact_amount
            
            # Round directly to nearest dollar for cash distribution (e.g., $43.1725 → $43)
            partner["tip_amount"] = round(exact_amount)
        
        # Distribute bills
        denominations = [20, 10, 5, 1]
        
        # Determine starting partner index based on rotation
        num_partners = len(partner_data)
        start_index = (session.get('week_counter', 1) - 1) % num_partners
        
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
        
        # Save to session
        session['distributed_tips'] = partner_data
        session['total_tip_amount'] = total_tip_amount
        session['hourly_rate'] = hourly_rate
        
        # Increment week counter for the next allocation
        session['week_counter'] = session.get('week_counter', 1) + 1
        
        return jsonify({
            'success': True,
            'partner_data': partner_data,
            'hourly_rate': hourly_rate,
            'total_tip_amount': total_tip_amount,
            'total_hours': total_hours
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/save_to_history', methods=['POST'])
def save_to_history():
    if 'distributed_tips' not in session:
        return jsonify({'error': 'No tip distribution available'}), 400
    
    try:
        distribution = {
            "week": session.get('week_counter', 1) - 1,
            "total_amount": session.get('total_tip_amount', 0),
            "total_hours": session.get('total_hours', 0),
            "partners": session.get('distributed_tips', [])
        }
        
        # Initialize history if needed
        if 'tips_history' not in session:
            session['tips_history'] = []
        
        # Get current history and append new item
        tips_history = session['tips_history']
        tips_history.append(distribution)
        
        # Update session
        session['tips_history'] = tips_history
        
        return jsonify({
            'success': True,
            'message': 'Distribution saved to history',
            'history': tips_history
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/get_history', methods=['GET'])
def get_history():
    tips_history = session.get('tips_history', [])
    return jsonify({'history': tips_history})

@app.route('/manual_partner_data', methods=['POST'])
def manual_partner_data():
    try:
        data = request.get_json()
        manual_partner_data = data.get('partnerData', [])
        
        if not all(partner.get('name') for partner in manual_partner_data):
            return jsonify({'error': 'Please provide names for all partners'}), 400
        
        # Calculate total hours
        total_hours = sum(float(partner.get('hours', 0)) for partner in manual_partner_data)
        
        # Store in session
        session['partner_data'] = manual_partner_data
        session['total_hours'] = total_hours
        
        return jsonify({
            'success': True, 
            'partner_data': manual_partner_data,
            'total_hours': total_hours
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/download_ocr', methods=['GET'])
def download_ocr():
    if 'ocr_result' not in session:
        return jsonify({'error': 'No OCR result available'}), 400
    
    ocr_result = session.get('ocr_result', '')
    b64 = base64.b64encode(ocr_result.encode()).decode()
    
    return jsonify({
        'success': True,
        'b64data': b64,
        'filename': 'ocr_result.txt'
    })

@app.route('/download_html', methods=['GET'])
def download_html():
    if 'distributed_tips' not in session:
        return jsonify({'error': 'No tip distribution available'}), 400
    
    try:
        # Get distribution data
        partner_data = session.get('distributed_tips', [])
        total_tip_amount = session.get('total_tip_amount', 0)
        total_hours = session.get('total_hours', 0)
        hourly_rate = session.get('hourly_rate', 0)
        
        # Format into tip data structure
        tip_data = []
        for partner in partner_data:
            exact_amount = partner.get('exact_tip_amount', 0)
            calculation = f"{partner.get('hours', 0)} × ${hourly_rate:.2f} = ${exact_amount:.2f}"
            
            tip_data.append({
                "Partner Name": partner.get("name", ""),
                "#": partner.get("number", ""),
                "Hours": partner.get("hours", 0),
                "Calculation": calculation,
                "Cash Amount": f"${partner.get('tip_amount', 0)}",
                "Bills": partner.get("bills_text", "")
            })
        
        # Generate HTML table
        html_content = generate_html_table(tip_data, total_tip_amount, total_hours, hourly_rate)
        html_b64 = base64.b64encode(html_content.encode()).decode()
        
        return jsonify({
            'success': True,
            'b64data': html_b64,
            'filename': 'tip_distribution.html'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def generate_html_table(tip_data, total_tip_amount, total_hours, hourly_rate):
    """Generate an HTML table for the tip distribution results"""
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

if __name__ == '__main__':
    app.run(debug=True)
