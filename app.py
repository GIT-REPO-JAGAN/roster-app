import os
import json
import uuid
import pandas as pd
from flask import Flask, request, jsonify, render_template, send_file
from groq import Groq
from werkzeug.utils import secure_filename
from openpyxl import load_workbook, Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from datetime import datetime, timedelta
import calendar

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'outputs'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

SHIFT_LEGEND = {
    "G":    "9:30 AM – 6:30 PM",
    "M":    "5:30 AM – 2:30 PM",
    "A":    "1:30 PM – 10:30 PM",
    "N":    "9:30 PM – 6:30 AM",
    "E":    "5:30 PM – 2:30 AM",
    "E1":   "7:30 PM – 4:30 AM",
    "WO":   "Weekly Off",
    "PL":   "Planned Leave",
    "COFF": "Compensatory Off",
    "H":    "Holiday",
    "SL":   "Sick Leave",
}

def read_roster(filepath):
    df = pd.read_excel(filepath, header=None)
    employees = []
    for i, row in df.iterrows():
        val = str(row[0]).strip() if pd.notna(row[0]) else ""
        if val in ("", "Month", "Date", "Day") or val.startswith("G (") or val.startswith("M (") \
           or val.startswith("A (") or val.startswith("N (") or val.startswith("E (") \
           or val.startswith("E1") or val in ("WO","PL","COFF","Holiday","SL"):
            continue
        if pd.notna(row[0]) and pd.notna(row[1]):
            employees.append({
                "name":     str(row[0]).strip(),
                "email":    str(row[1]).strip(),
                "skill":    str(row[2]).strip() if pd.notna(row[2]) else "",
                "location": str(row[3]).strip() if pd.notna(row[3]) else "",
            })
    return employees

def build_groq_prompt(employees, start_date, end_date):
    emp_list = "\n".join([f"  - {e['name']} | {e['email']} | {e['skill']} | {e['location']}"
                          for e in employees])
    return f"""You are an expert Excel workforce scheduling assistant.

TASK: Generate a shift schedule JSON for the given employees and date range.

DATE RANGE: {start_date} to {end_date}

EMPLOYEES:
{emp_list}

SHIFT CODES:
  G=9:30AM-6:30PM, M=5:30AM-2:30PM, A=1:30PM-10:30PM, N=9:30PM-6:30AM,
  E=5:30PM-2:30AM, E1=7:30PM-4:30AM, WO=Weekly Off, PL=Planned Leave,
  COFF=Compensatory Off, H=Holiday, SL=Sick Leave

CHAIN-OF-THOUGHT:
Step 1: Parse the date range and enumerate every calendar day.
Step 2: Mark all Saturdays and Sundays as WO.
Step 3: For each employee, assign a consistent shift rotation on weekdays.
        Distribute shifts realistically: mix of G, M, A, N, E, E1 shifts.
        Occasionally insert PL or SL (1-2 days per employee per month max).
Step 4: Ensure each employee has exactly one shift code per day.
Step 5: Return ONLY valid JSON — no markdown, no explanation.

OUTPUT FORMAT (strict JSON, no extra text):
{{
  "schedule": {{
    "EMPLOYEE_NAME": {{
      "YYYY-MM-DD": "SHIFT_CODE",
      ...
    }},
    ...
  }}
}}

Rules:
- Every date in range must have an entry for every employee
- Weekends must be WO
- Use realistic shift distribution
- Return ONLY the JSON object, nothing else"""

def call_groq(api_key, prompt):
    client = Groq(api_key=api_key)
    response = client.chat.completions.create(
        model="llama3-70b-8192",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=8000,
    )
    return response.choices[0].message.content.strip()

def generate_excel(employees, schedule_data, start_date_str, end_date_str, output_path):
    start = datetime.strptime(start_date_str, "%Y-%m-%d")
    end   = datetime.strptime(end_date_str,   "%Y-%m-%d")
    dates = [start + timedelta(days=i) for i in range((end - start).days + 1)]

    wb = Workbook()
    ws = wb.active
    ws.title = "Sheet1"

    # Styles
    bold_center = {"font": Font(name="Arial", size=10, bold=True),
                   "alignment": Alignment(horizontal="center", vertical="center")}
    normal_left  = {"font": Font(name="Arial", size=10),
                    "alignment": Alignment(horizontal="left", vertical="center")}
    normal_center= {"font": Font(name="Arial", size=10),
                    "alignment": Alignment(horizontal="center", vertical="center")}
    grey_fill    = PatternFill("solid", fgColor="D9D9D9")
    header_fill  = PatternFill("solid", fgColor="1F4E79")
    month_fills  = [PatternFill("solid", fgColor="2E75B6"),
                    PatternFill("solid", fgColor="70AD47")]
    white_font   = Font(name="Arial", size=10, bold=True, color="FFFFFF")
    thin_border  = Border(
        left=Side(style="thin", color="CCCCCC"),
        right=Side(style="thin", color="CCCCCC"),
        top=Side(style="thin", color="CCCCCC"),
        bottom=Side(style="thin", color="CCCCCC"),
    )

    # Fixed header columns A-D
    for row in range(1, 4):
        for col in range(1, 5):
            cell = ws.cell(row=row, column=col)
            cell.fill = header_fill
            cell.font = white_font
            cell.alignment = Alignment(horizontal="center", vertical="center")
    ws.cell(row=1, column=1).value = "Month"
    ws.cell(row=2, column=1).value = "Date"
    ws.cell(row=3, column=1).value = "Day"
    for col, lbl in enumerate(["Name", "Email", "Skill", "Location"], start=1):
        ws.cell(row=3, column=col).value = lbl

    # Build month groups for merging
    month_groups = {}
    for i, d in enumerate(dates):
        key = d.strftime("%b %Y")
        if key not in month_groups:
            month_groups[key] = {"start": i, "end": i}
        else:
            month_groups[key]["end"] = i

    # Date header columns
    col_offset = 5
    prev_month_idx = 0
    for i, d in enumerate(dates):
        col = col_offset + i
        col_letter = get_column_letter(col)
        is_weekend = d.weekday() >= 5

        # Row 2: date number
        c2 = ws.cell(row=2, column=col, value=d.day)
        c2.font = Font(name="Arial", size=9, bold=True,
                       color="FFFFFF" if not is_weekend else "333333")
        c2.alignment = Alignment(horizontal="center", vertical="center")
        c2.fill = grey_fill if is_weekend else PatternFill("solid", fgColor="2E75B6")

        # Row 3: day name
        c3 = ws.cell(row=3, column=col, value=d.strftime("%a"))
        c3.font = Font(name="Arial", size=9, bold=True,
                       color="555555" if is_weekend else "FFFFFF")
        c3.alignment = Alignment(horizontal="center", vertical="center")
        c3.fill = grey_fill if is_weekend else PatternFill("solid", fgColor="1F4E79")

        ws.column_dimensions[col_letter].width = 5

    # Row 1: month name merged
    month_fill_idx = 0
    for month_key, span in month_groups.items():
        start_col = col_offset + span["start"]
        end_col   = col_offset + span["end"]
        ws.merge_cells(start_row=1, start_column=start_col,
                       end_row=1, end_column=end_col)
        mc = ws.cell(row=1, column=start_col, value=month_key)
        mc.font  = white_font
        mc.fill  = month_fills[month_fill_idx % len(month_fills)]
        mc.alignment = Alignment(horizontal="center", vertical="center")
        month_fill_idx += 1

    # Employee rows
    shift_colors = {
        "G": "E2EFDA", "M": "DDEBF7", "A": "FFF2CC",
        "N": "F4CCCC", "E": "EAD1DC", "E1": "D9D2E9",
        "WO": "F2F2F2", "PL": "FCE5CD", "COFF": "D0E4F5",
        "H":  "FFE599", "SL": "EA9999",
    }

    for row_idx, emp in enumerate(employees):
        row = 4 + row_idx
        row_bg = PatternFill("solid", fgColor="F7FBFF" if row_idx % 2 == 0 else "FFFFFF")

        for col, val in enumerate([emp["name"], emp["email"], emp["skill"], emp["location"]], 1):
            c = ws.cell(row=row, column=col, value=val)
            c.font      = Font(name="Arial", size=10)
            c.alignment = Alignment(horizontal="left", vertical="center")
            c.fill      = row_bg
            c.border    = thin_border

        for i, d in enumerate(dates):
            col = col_offset + i
            date_key   = d.strftime("%Y-%m-%d")
            shift_code = schedule_data.get(emp["name"], {}).get(date_key, "WO" if d.weekday() >= 5 else "")
            c = ws.cell(row=row, column=col, value=shift_code)
            fill_color = shift_colors.get(shift_code, "FFFFFF")
            c.fill      = PatternFill("solid", fgColor=fill_color)
            c.font      = Font(name="Arial", size=9)
            c.alignment = Alignment(horizontal="center", vertical="center")
            c.border    = thin_border

    # Column widths A-D
    ws.column_dimensions["A"].width = 28
    ws.column_dimensions["B"].width = 32
    ws.column_dimensions["C"].width = 22
    ws.column_dimensions["D"].width = 14

    # Row heights
    ws.row_dimensions[1].height = 18
    ws.row_dimensions[2].height = 16
    ws.row_dimensions[3].height = 16

    # Freeze panes
    ws.freeze_panes = "E4"

    # Legend block
    legend_start_row = 4 + len(employees) + 2
    ws.cell(row=legend_start_row, column=1, value="SHIFT LEGEND").font = \
        Font(name="Arial", size=10, bold=True)
    for i, (code, desc) in enumerate(SHIFT_LEGEND.items()):
        r = legend_start_row + 1 + i
        c1 = ws.cell(row=r, column=1, value=code)
        c1.font = Font(name="Arial", size=10, bold=True)
        fill_color = shift_colors.get(code, "FFFFFF")
        c1.fill = PatternFill("solid", fgColor=fill_color)
        c1.alignment = Alignment(horizontal="center")
        ws.cell(row=r, column=2, value=desc).font = Font(name="Arial", size=10)

    wb.save(output_path)

# ── Routes ──────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/generate", methods=["POST"])
def generate():
    api_key    = request.form.get("api_key", "").strip()
    start_date = request.form.get("start_date", "").strip()
    end_date   = request.form.get("end_date", "").strip()
    file       = request.files.get("roster_file")

    if not all([api_key, start_date, end_date, file]):
        return jsonify({"error": "All fields are required."}), 400

    try:
        datetime.strptime(start_date, "%Y-%m-%d")
        datetime.strptime(end_date,   "%Y-%m-%d")
    except ValueError:
        return jsonify({"error": "Invalid date format. Use YYYY-MM-DD."}), 400

    filename = secure_filename(file.filename)
    upload_path = os.path.join(UPLOAD_FOLDER, f"{uuid.uuid4()}_{filename}")
    file.save(upload_path)

    try:
        employees = read_roster(upload_path)
        if not employees:
            return jsonify({"error": "No employees found in the roster file."}), 400

        prompt        = build_groq_prompt(employees, start_date, end_date)
        groq_response = call_groq(api_key, prompt)

        # Parse JSON from Groq
        raw = groq_response.strip()
        if raw.startswith("```"):
            raw = "\n".join(raw.split("\n")[1:])
        if raw.endswith("```"):
            raw = "\n".join(raw.split("\n")[:-1])
        schedule_data = json.loads(raw).get("schedule", {})

        output_id   = str(uuid.uuid4())
        output_path = os.path.join(OUTPUT_FOLDER, f"schedule_{output_id}.xlsx")
        generate_excel(employees, schedule_data, start_date, end_date, output_path)

        return jsonify({
            "success":       True,
            "download_id":   output_id,
            "employee_count": len(employees),
            "message":       f"Schedule generated for {len(employees)} employees."
        })

    except json.JSONDecodeError as e:
        return jsonify({"error": f"AI returned invalid JSON: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if os.path.exists(upload_path):
            os.remove(upload_path)

@app.route("/api/download/<download_id>")
def download(download_id):
    safe_id = secure_filename(download_id)
    path    = os.path.join(OUTPUT_FOLDER, f"schedule_{safe_id}.xlsx")
    if not os.path.exists(path):
        return jsonify({"error": "File not found or expired."}), 404
    return send_file(path, as_attachment=True,
                     download_name="Roster_Schedule_Output.xlsx",
                     mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
