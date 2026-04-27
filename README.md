⚡ ShiftAI — AI-Powered Roster Shift Scheduler
> Upload a staff roster, pick a date range, and let **Groq LLaMA3-70B** generate a fully formatted Excel shift schedule in seconds.
---
✨ Features
📂 Upload any `.xlsx` roster — Name, Email, Skill, Location
🤖 Groq AI generates realistic shift assignments using LLaMA3-70B
📅 Full date-range support — spans multiple months automatically
📊 Formatted Excel output — merged month headers, colour-coded shifts, freeze panes, weekend highlights
⬇ One-click download of the finished schedule
🎨 Dark-mode UI — clean, modern, mobile-responsive
---
🚀 Quick Start (GitHub Codespaces — Recommended)
Click Code → Open with Codespaces → New codespace on this repo
Wait ~60 seconds for the environment to auto-install and start
The app opens automatically at `http://localhost:5000`
Enter your Groq API key, upload your roster, set dates, click Generate
> No local setup needed. Everything runs in the browser.
---
💻 Local Setup
Prerequisites
Python 3.9+
pip
Steps
```bash
# 1. Clone the repo
git clone https://github.com/YOUR_USERNAME/roster-shift-scheduler.git
cd roster-shift-scheduler

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. (Optional) Set environment variables
cp .env.example .env
# Edit .env if needed

# 5. Run the app
python app.py
```
Open http://localhost:5000 in your browser.
---
📋 Input File Format
Your roster `.xlsx` must follow this structure:
Column A	Column B	Column C	Column D
Month	Email	Skill	Location
Date			
Day			
John Doe	john@co.com	Azure SME	Bangalore
Jane Smith	jane@co.com	Monitoring	Chennai
Rows 1–3 are header rows. Employee data starts at Row 4.
---
📤 Output File Format
The generated `.xlsx` contains:
Row 1 — Month names (merged across days)
Row 2 — Day numbers (1–31)
Row 3 — Day abbreviations (Sun, Mon…)
Rows 4+ — Employee shift codes per day
Freeze panes at Column E / Row 4
Colour-coded shifts and greyed weekend columns
Shift legend preserved at the bottom
---
🔑 Shift Code Reference
Code	Shift	Hours
G	General	9:30 AM – 6:30 PM
M	Morning	5:30 AM – 2:30 PM
A	Afternoon	1:30 PM – 10:30 PM
N	Night	9:30 PM – 6:30 AM
E	Evening	5:30 PM – 2:30 AM
E1	Late Eve	7:30 PM – 4:30 AM
WO	Weekly Off	—
PL	Planned Leave	—
COFF	Comp Off	—
H	Holiday	—
SL	Sick Leave	—
---
🌐 API Endpoints
Method	Endpoint	Description
GET	`/`	Web UI
POST	`/api/generate`	Generate schedule (multipart form)
GET	`/api/download/<id>`	Download generated `.xlsx`
POST `/api/generate` fields:
Field	Type	Description
`api_key`	string	Your Groq API key
`roster_file`	file	`.xlsx` roster file
`start_date`	string	`YYYY-MM-DD`
`end_date`	string	`YYYY-MM-DD`
---
🗂 Project Structure
```
roster-shift-scheduler/
├── app.py                      # Flask backend + AI integration
├── requirements.txt            # Python dependencies
├── Procfile                    # Gunicorn config
├── .env.example                # Environment variable template
├── .gitignore
├── .devcontainer/
│   └── devcontainer.json       # GitHub Codespaces config
├── .github/
│   └── workflows/
│       └── ci.yml              # GitHub Actions CI
├── templates/
│   └── index.html              # Main UI
├── static/
│   ├── css/style.css
│   └── js/app.js
├── uploads/                    # Temp upload dir (git-ignored)
└── outputs/                    # Generated files (git-ignored)
```
---
🔒 Security Notes
API keys are never stored server-side — passed per-request only
Uploaded files are deleted immediately after processing
Generated files are stored temporarily with a UUID filename
---
🤝 Contributing
Fork the repo
Create a feature branch: `git checkout -b feature/my-change`
Commit and push
Open a Pull Request
---
📄 License
MIT — free to use, modify, and distribute.
