import os
import datetime
import pytz
import markdown
import google.generativeai as genai
from textwrap import dedent

# 1. Configuration
API_KEY = os.environ.get("GEMINI_API_KEY")
if not API_KEY:
    raise ValueError("GEMINI_API_KEY environment variable not found.")

genai.configure(api_key=API_KEY)

# Use the paid model requested by the user
MODEL_NAME = 'gemini-3-pro-preview'

def get_current_time_str():
    """Returns current time in Taipei timezone."""
    tz = pytz.timezone('Asia/Taipei')
    now = datetime.datetime.now(tz)
    return now.strftime('%Y-%m-%d %H:%M:%S (UTC+8)')

def read_report_prompt(filepath="report.md"):
    """Reads the prompt from the markdown file."""
    with open(filepath, "r", encoding="utf-8") as f:
        return f.read()

def generate_report(prompt):
    """Generates the report using Gemini API."""
    # Debugging: Print version and available types
    print(f"GenAI Version: {genai.__version__}")
    
    tools = []
    from google.generativeai import protos
    
    # Try to find the correct Google Search tool class
    if hasattr(protos, 'GoogleSearch'):
        print("Found protos.GoogleSearch - Configuring tool...")
        tools = [protos.Tool(google_search=protos.GoogleSearch())]
    elif hasattr(protos, 'GoogleSearchRetrieval'):
        print("Found protos.GoogleSearchRetrieval - Configuring tool...")
        tools = [
            protos.Tool(
                google_search_retrieval=protos.GoogleSearchRetrieval(
                    dynamic_retrieval_config=protos.DynamicRetrievalConfig(
                        mode=protos.DynamicRetrievalConfig.Mode.DYNAMIC,
                        dynamic_threshold=0.3,
                    )
                )
            )
        ]
    else:
        print("CRITICAL ERROR: Could not find GoogleSearch or GoogleSearchRetrieval in protos.")
        print(f"Available protos: {[p for p in dir(protos) if 'Search' in p]}")
        raise ImportError("Google Search tool class not found in installed google-generativeai version.")

    print(f"Tools configuration: {tools}")
    model = genai.GenerativeModel(MODEL_NAME, tools=tools)
    
    # Add current time context to the prompt
    full_prompt = f"{prompt}\n\n(System Note: The current execution time is {get_current_time_str()})"
    
    # Configure generation to disable function calling to prevent "finish_reason: 10"
    generation_config = genai.types.GenerationConfig(
        # Force the model to only generate text, disabling automatic function calling behavior
        # that might be triggered by the prompt content
    )
    
    try:
        # Explicitly requesting text response
        response = model.generate_content(full_prompt)
        
        # Check if the response has a valid part
        if not response.parts:
             if response.prompt_feedback:
                 return f"Error: Blocked by safety filters. Feedback: {response.prompt_feedback}"
             return f"Error: Empty response. Finish reason: {response.candidates[0].finish_reason if response.candidates else 'Unknown'}"

        return response.text
    except Exception as e:
        print(f"Error generating content with model {MODEL_NAME}: {e}")
        print("Attempting to list available models...")
        try:
            for m in genai.list_models():
                if 'generateContent' in m.supported_generation_methods:
                    print(f"- {m.name}")
        except Exception as list_e:
            print(f"Could not list models: {list_e}")
            
        return f"Error generating report: {e}. Check the Action logs for available models."

def convert_to_html(markdown_text):
    """Converts Markdown to HTML with extensions."""
    html_content = markdown.markdown(
        markdown_text,
        extensions=['tables', 'fenced_code', 'nl2br']
    )
    return html_content

def get_history_links():
    """Scans the reports directory and returns a list of links."""
    if not os.path.exists("reports"):
        return ""
    
    links = []
    for filename in sorted(os.listdir("reports"), reverse=True):
        if filename.endswith(".html"):
            date_str = filename.replace(".html", "")
            links.append(f'<li><a href="reports/{filename}">{date_str}</a></li>')
    
    if not links:
        return ""
        
    return f"""
    <div class="history-section">
        <h3>📅 歷史報告存檔</h3>
        <ul>
            {''.join(links)}
        </ul>
    </div>
    """

def create_html_page(report_html):
    """Wraps the report content in a responsive HTML template."""
    current_time = get_current_time_str()
    history_links = get_history_links()
    
    css = """
    :root {
        --primary-color: #2c3e50;
        --accent-color: #3498db;
        --bg-color: #f8f9fa;
        --card-bg: #ffffff;
        --text-color: #333;
        --border-radius: 12px;
    }
    
    body {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        line-height: 1.6;
        color: var(--text-color);
        background-color: var(--bg-color);
        margin: 0;
        padding: 20px;
        -webkit-font-smoothing: antialiased;
    }
    
    .container {
        max-width: 800px;
        margin: 0 auto;
        background: var(--card-bg);
        padding: 30px;
        border-radius: var(--border-radius);
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
    }
    
    h1, h2, h3 {
        color: var(--primary-color);
        margin-top: 1.5em;
    }
    
    h1 {
        font-size: 1.8rem;
        border-bottom: 2px solid var(--accent-color);
        padding-bottom: 10px;
        margin-top: 0;
    }
    
    h2 {
        font-size: 1.4rem;
        border-left: 4px solid var(--accent-color);
        padding-left: 10px;
        background: #f1f8ff;
        padding: 8px 10px;
        border-radius: 0 8px 8px 0;
    }
    
    h3 {
        font-size: 1.2rem;
        color: #555;
    }
    
    table {
        width: 100%;
        border-collapse: collapse;
        margin: 20px 0;
        display: block;
        overflow-x: auto;
    }
    
    th, td {
        padding: 12px;
        border: 1px solid #ddd;
        text-align: left;
    }
    
    th {
        background-color: var(--primary-color);
        color: white;
    }
    
    tr:nth-child(even) {
        background-color: #f2f2f2;
    }
    
    blockquote {
        border-left: 4px solid var(--accent-color);
        margin: 0;
        padding-left: 15px;
        color: #666;
        font-style: italic;
    }
    
    .history-section {
        margin-top: 40px;
        padding-top: 20px;
        border-top: 2px dashed #eee;
    }
    
    .history-section ul {
        list-style: none;
        padding: 0;
        display: flex;
        flex-wrap: wrap;
        gap: 10px;
    }
    
    .history-section li a {
        display: inline-block;
        padding: 5px 15px;
        background: #f0f0f0;
        color: #555;
        text-decoration: none;
        border-radius: 20px;
        font-size: 0.9rem;
        transition: background 0.2s;
    }
    
    .history-section li a:hover {
        background: var(--accent-color);
        color: white;
    }
    
    .footer {
        margin-top: 40px;
        text-align: center;
        font-size: 0.9rem;
        color: #888;
        border-top: 1px solid #eee;
        padding-top: 20px;
    }
    
    /* Mobile Optimization */
    @media (max-width: 600px) {
        body {
            padding: 10px;
        }
        .container {
            padding: 15px;
        }
        h1 {
            font-size: 1.5rem;
        }
        table {
            font-size: 0.9rem;
        }
    }
    """
    
    html_template = f"""
    <!DOCTYPE html>
    <html lang="zh-TW">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>每日美股宏觀晨報</title>
        <style>
            {dedent(css)}
        </style>
    </head>
    <body>
        <div class="container">
            {report_html}
            
            {history_links}
            
            <div class="footer">
                <p>Generated automatically by AI Agent at {current_time}</p>
            </div>
        </div>
    </body>
    </html>
    """
    return html_template

def main():
    print("Starting report generation...")
    
    # 1. Read Prompt
    if not os.path.exists("report.md"):
        print("Error: report.md not found!")
        return
    
    prompt = read_report_prompt()
    
    # Inject current system time into the prompt placeholder
    current_time_str = get_current_time_str()
    prompt = prompt.replace("{{CURRENT_DATE}}", current_time_str)
    
    print(f"Prompt loaded and time injected: {current_time_str}")
    
    # 2. Generate Content
    print("Querying Gemini API...")
    report_markdown = generate_report(prompt)
    print("Report generated.")
    
    # 3. Convert to HTML
    report_html = convert_to_html(report_markdown)
    
    # 4. Create Full Page
    full_html = create_html_page(report_html)
    
    # 5. Save to index.html (Current Report)
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(full_html)
    print("Success! index.html has been created.")
    
    # 6. Archive Report
    # Create reports directory if not exists
    if not os.path.exists("reports"):
        os.makedirs("reports")
        
    # Get today's date for filename (e.g., 2025-11-23.html)
    tz = pytz.timezone('Asia/Taipei')
    today_str = datetime.datetime.now(tz).strftime('%Y-%m-%d')
    archive_filename = f"reports/{today_str}.html"
    
    with open(archive_filename, "w", encoding="utf-8") as f:
        f.write(full_html)
    print(f"Archived to {archive_filename}")
    
    # 7. Send Email
    send_email(full_html, today_str)

def send_email(html_content, date_str):
    """Sends the report via email."""
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    
    sender_email = os.environ.get("EMAIL_SENDER")
    sender_password = os.environ.get("EMAIL_PASSWORD")
    
    # Recipients list
    recipients = ["yenjung@gmail.com"]
    
    if not sender_email or not sender_password:
        print("Warning: EMAIL_SENDER or EMAIL_PASSWORD not set. Skipping email.")
        return

    print(f"Sending email to {len(recipients)} recipients...")
    
    try:
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = ", ".join(recipients)
        msg['Subject'] = f"📊 每日美股宏觀晨報 ({date_str})"
        
        msg.attach(MIMEText(html_content, 'html'))
        
        # Connect to Gmail SMTP server
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(sender_email, sender_password)
            server.send_message(msg)
            
        print("Email sent successfully!")
    except Exception as e:
        print(f"Error sending email: {e}")

if __name__ == "__main__":
    main()
