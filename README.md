# TipJar

A Streamlit application that automates tip allocation and cash distribution for service teams using OCR (Optical Character Recognition) to process partner hours from PDFs or images.

## Features

- **Dual AI Provider Support**: 
  - Mistral AI for both PDF and Image OCR
  - Gemini AI for Image OCR

- **Multiple Document Types**:
  - PDF documents (Mistral only)
  - Images (JPG, JPEG, PNG)

- **Flexible Input Methods**:
  - URL input for online documents
  - Local file upload

- **Tip Distribution Functions**:
  - Extract partner hours from documents
  - Calculate tip allocation based on hours worked
  - Distribute bills equitably among partners
  - Track distribution history
  - Generate copy-paste ready outputs

## How It Works

1. **Hour Processing**:
   - Process partner hours from PDF/image input
   - Sum total hours worked

2. **Tip Allocation**:
   - Calculate individual tips using the formula: (Individual Hours ÷ Total Hours) × Total Tips
   - Apply strict downward rounding (e.g., $58.99 → $58)

3. **Bill Distribution**:
   - Distribute available bills [$20, $10, $5, $1] equitably
   - Rotate starting partner weekly to ensure fairness
   - Prevent denomination bias

4. **Output Format**:
   - Partner Name | # | Hours | Tip Amount | Bills
   - Example: Alex | #3 | 38h | $224 | 4x$20,2x$10,4x$1

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd <repository-directory>
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
# On Windows
venv\Scripts\activate
# On Unix or MacOS
source venv/bin/activate
```

3. Install the required packages:
```bash
pip install -r requirements.txt
```

4. Configure API keys:
```bash
# Copy the sample environment file
cp sample.env .env

# Edit the .env file with your actual API keys
# On Windows
notepad .env
# On Unix/MacOS
nano .env
```

## API Keys Required

- **Mistral AI**: Get your API key from [Mistral AI Console](https://console.mistral.ai/api-keys)
- **Gemini AI**: Get your API key from [Google AI Studio](https://makersuite.google.com/app/apikey)

Add your API keys to the `.env` file:
```
MISTRAL_API_KEY=your_mistral_api_key_here
GEMINI_API_KEY=your_gemini_api_key_here
```

## Usage

1. Run the Streamlit app:
```bash
streamlit run main.py
```

2. Select your preferred AI provider (Mistral or Gemini)

3. Choose document type (PDF/Image) and source type (URL/Local Upload)

4. Process your document to extract partner hours

5. Enter the total tip amount and calculate the tip distribution

6. View and save your results

## Example Workflow

For a total of $875 in tips for 148 hours worked:
- Partner 1 (40h → $236.48 → $236)
- Partner 2 (32h → $189.19 → $189)
- Partner 3 (38h → $224.65 → $224)
- Partner 4 (38h → $224.65 → $224)

With week 3 rotation starting with the last partner, the output might look like:
- Alex | #3 | 38h | $224 | 4x$20,2x$10,4x$1

## Features in Detail

### OCR Processing
- **Mistral OCR**: 
  - Supports both PDF and image processing
  - Maintains document structure and formatting
  - Works with both local files and URLs

- **Gemini Vision**: 
  - Specialized in image processing
  - Provides detailed text extraction with context
  - Currently does not support PDFs

### Partner Data Extraction
- AI-assisted extraction of names and hours
- Manual data entry option for corrections

### Tip Calculation
- Mathematically fair distribution based on hours worked
- Strict downward rounding to ensure no overpayment

### Bill Distribution
- Equitable distribution of bills
- Weekly rotation to ensure fairness over time
- Tracking of distribution history

## API Key Security

This application uses a `.env` file to securely store your API keys. The file is:

- Excluded from version control via `.gitignore`
- Loaded at runtime using `python-dotenv`
- Only accessible within the application

If you need to update your API keys, simply edit the `.env` file - no need to modify the code.

## Limitations

- Gemini AI does not currently support PDF processing
- PDF preview may require browser PDF plugin support
- Maximum file size limits apply based on the AI provider's restrictions
- OCR accuracy depends on document quality and formatting

## Troubleshooting

If you encounter issues:

1. **API Key Configuration**:
   - Ensure you've created a `.env` file with the correct API keys
   - Check for any typos in your API keys
   - Verify that your API keys are still valid and not expired

2. **PDF Preview Not Working**:
   - Ensure your browser supports PDF viewing
   - Try using a different browser
   - Check if the PDF URL is accessible

3. **OCR Not Working**:
   - Verify your API key is correct
   - Check if the document is in a supported format
   - Ensure the document is readable and not corrupted

4. **Partner Data Extraction Issues**:
   - Try using the manual data entry option
   - Check if names and hours are clearly visible in the document
   - Improve document quality if possible

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details. 
