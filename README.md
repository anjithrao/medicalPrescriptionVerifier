Prescription OCR

An AI-powered handwritten prescription understanding system that extracts medicine names from prescription images and presents patient-friendly medicine information.

The project combines OCR, transformer-based handwriting recognition, fuzzy correction, and LLM-assisted validation to improve recognition of handwritten medical prescriptions.

Features
Upload handwritten prescription images
Prescription crop and preprocessing
EasyOCR-based text detection
TrOCR-based handwritten medicine recognition
Fuzzy medicine name correction
Gemini-assisted medicine extraction and validation
Medicine usage and side-effect information
Translation into Indian languages
Nearby pharmacy discovery
Route guidance to pharmacies
Text-to-speech medicine summaries
Tech Stack
Frontend
React
Vite
Tailwind CSS
Three.js
Backend
Flask
Python
Machine Learning
TrOCR
EasyOCR
PyTorch
Transformers
External Services
Gemini API
OpenStreetMap
Overpass API
OSRM Routing
Architecture
User Upload
↓
Image Processing
↓
EasyOCR Detection
↓
TrOCR Recognition
↓
Fuzzy Correction
↓
Gemini Validation
↓
Medicine Information
↓
Frontend Results
Project Structure
src/ React frontend
templates/ Flask templates
static/ Static assets
app.py Flask backend
medicines.txt Medicine dictionary
info_txt.txt Medicine information
requirements.txt Python dependencies
Running Locally
Backend
pip install -r requirements.txt
python app.py
Frontend
npm install
npm run dev
Future Improvements
Multi-language prescription recognition
Improved medicine detection models
Cloud deployment
Human-in-the-loop verification workflow

The trained TrOCR model is hosted separately due to GitHub file size limits.

Run:

```bash
python download_model.py

Author

Anjith
B.Tech CSE

VNR Vignana Jyothi Institute of Engineering and Technology
```
