import os
import json
import uuid
import pandas as pd
from flask import Flask, request, jsonify, render_template, send_file
from groq import Groq
from werkzeug.utils import secure_filename
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from datetime import datetime, timedelta

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'outputs'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

SHIFT_LEGEND = {
    "G": "9:30 AM – 6:30 PM", "M": "5:30 AM – 2:30 PM", "A": "1:30 PM – 10:30 PM",
    "N": "9:30 PM – 6:30 AM", "E": "5:30 PM – 2:30 AM", "E1": "7:30 PM – 4:30 AM",
    "WO": "Weekly Off", "PL": "Planned Leave", "COFF": "Compensatory Off",
    "H": "Holiday", "SL": "Sick Leave",
}

def read_roster(filepath):
    df = pd.read_excel(filepath, header=None)
    employees = []
    for i, row in df.iterrows():
        val = str(row[0]).strip() if pd.notna(row[0]) else ""
        if val in ("", "Month", "Date", "Day") or any(val.startswith(p) for p in ["G (", "M (", "A (", "N (", "E (", "E1"]) or val in ("WO","PL","COFF","Holiday","SL"):
            continue
        if pd.notna(row[0]) and pd.notna(row[1]):
            employees.append({
                "name": str(row[0]).strip(), "email": str(row[1]).strip(),
                "skill": str(row[2]).strip() if pd.notna(row[2]) else "",
                "location": str(row[3]).strip() if pd.notna(row[3]) else "",
            })
    return employees

def build_groq_prompt(employees, start_date, end_date, custom_prompt):
    emp_list = "\n".join([f"  - {e['name']} | {e['email']} | {e['skill']} | {e['location']}" for e in employees])
    return f"""You are a Workforce Scheduling Engine. 
    TASK: Generate a shift schedule JSON.
    DATE RANGE: {start_date} to {end_date}
    EMPLOYEES:
    {emp_list}

    SHIFT CODES: G, M, A, N, E, E1, WO, PL, COFF, H, SL

    USER SPECIFIC CONSTRAINTS (PRIORITY):
    {custom_prompt if custom_prompt else "No specific constraints provided."}

    STRICT RULES:
    1. prioritize the USER SPECIFIC CONSTRAINTS above all else.
    2. Every employee must have exactly one shift code per day.
    3. Weekends (Sat/Sun) are WO by default unless the user constraints specify otherwise.
    4. Return ONLY a raw JSON object. No explanation, no markdown blocks.

    OUTPUT FORMAT:
    {{
      "schedule": {{
        "Employee Name": {{ "YYYY-MM-DD": "CODE" }}
      }}
    }}"""

def call_groq(api_key, prompt):
    client = Groq(api_key=api_key)
    response = client.chat.completions.create(
        model="llama3-70b-8192",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        max_tokens=8000,
    )
    return response.choices[0].message.content.strip()

def generate_excel(employees, schedule_data, start_date_str, end_date_str, output_path):
    start = datetime.strptime(start_date_str, "%Y-%m-%d")
    end = datetime.strptime(end_date_str, "%Y-%m-%d")
    dates = [start + timedelta(days=i) for i in range((end - start).days + 1)]

    wb = Workbook()
    ws = wb.active
    ws.title = "Shift Schedule"

    # Styles
    header_fill = PatternFill("solid", fgColor="1F4E79")
    white_font = Font(name="Arial", size=10, bold=True, color="FFFFFF")
    thin_border = Border(left=Side(style="thin", color="CCCCCC"), right=Side(style="thin", color="CCCCCC"),
                         top=Side(style="thin", color="CCCCCC"), bottom=Side(style="thin", color="CCCCCC"))

    # Static Headers
    for row in range(1, 4):
        for col in range(1, 5):
            cell = ws.cell(row=row, column=col)
            cell.fill = header_fill
            cell.font = white_font
            cell.alignment = Alignment(horizontal="center", vertical="center")
    
    ws.cell(row=1, column=1).value = "Month"
    ws.cell(row=2, column=1).value = "Date"
    ws.cell(row=3, column=1).value = "Day"
    for col, lbl in enumerate(["Name", "Email", "Skill", "Location"], 1):
        ws.cell(row=3, column=col).value = lbl

    col_offset = 5
    for i, d in enumerate(dates):
        col = col_offset + i
        is_weekend = d.weekday() >= 5
        c2 = ws.cell(row=2, column=col, value=d.day)
        c2.fill = PatternFill("solid", fgColor="D9D9D9" if is_weekend else "2E75B6")
        c2.font = white_font if not is_weekend else Font(color="333333")
        c3 = ws.cell(row=3, column=col, value=d.strftime("%a"))
        c3.fill = PatternFill("solid", fgColor="D9D9D9" if is_weekend else "1F4E79")
        c3.font = white_font if not is_weekend else Font(color="555555")
        ws.column_dimensions[get_column_letter(col)].width = 5

    shift_colors = {"G": "E2EFDA", "M": "DDEBF7", "A": "FFF2CC", "N": "F4CCCC", "E": "EAD1DC", "E1": "D9D2E9", "WO": "F2F2F2", "PL": "FCE5CD"}

    for row_idx, emp in enumerate(employees):
        row = 4 + row_idx
        for col, val in enumerate([emp["name"], emp["email"], emp["skill"], emp["location"]], 1):
            c = ws.cell(row=row, column=col, value=val)
            c.border = thin_border
        for i, d in enumerate(dates):
            col = col_offset + i
            date_key = d.strftime("%Y-%m-%d")
            shift_code = schedule_data.get(emp["name"], {}).get(date_key, "WO" if d.weekday() >= 5 else "")
            c = ws.cell(row=row, column=col, value=shift_code)
            c.fill = PatternFill("solid", fgColor=shift_colors.get(shift_code, "FFFFFF"))
            c.border = thin_border

    ws.column_dimensions["A"].width = 25
    ws.column_dimensions["B"].width = 30
    ws.freeze_panes = "E4"
    wb.save(output_path)

@app.route("/")
def index(): return render_template("index.html")

@app.route("/api/generate", methods=["POST"])
def generate():
    api_key = request.form.get("api_key", "").strip()
    start_date = request.form.get("start_date", "").strip()
    end_date = request.form.get("end_date", "").strip()
    custom_prompt = request.form.get("custom_prompt", "").strip()
    file = request.files.get("roster_file")

    if not all([api_key, start_date, end_date, file]):
        return jsonify({"error": "All fields are required."}), 400

    filename = secure_filename(file.filename)
    upload_path = os.path.join(UPLOAD_FOLDER, f"{uuid.uuid4()}_{filename}")
    file.save(upload_path)

    try:
        employees = read_roster(upload_path)
        prompt = build_groq_prompt(employees, start_date, end_date, custom_prompt)
        groq_response = call_groq(api_key, prompt)
        
        # Clean JSON
        raw = groq_response.strip()
        if raw.startswith("```"): raw = raw.split("\n", 1)[1].rsplit("\n", 1)[0]
        schedule_data = json.loads(raw).get("schedule", {})

        output_id = str(uuid.uuid4())
        output_path = os.path.join(OUTPUT_FOLDER, f"schedule_{output_id}.xlsx")
        generate_excel(employees, schedule_data, start_date, end_date, output_path)

        return jsonify({"success": True, "download_id": output_id, "employee_count": len(employees)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if os.path.exists(upload_path): os.remove(upload_path)

@app.route("/api/download/<download_id>")
def download(download_id):
    path = os.path.join(OUTPUT_FOLDER, f"schedule_{secure_filename(download_id)}.xlsx")
    return send_file(path, as_attachment=True) if os.path.exists(path) else jsonify({"error": "Not found"}), 404

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
