import sys

class SimplePDFWriter:
    def __init__(self):
        self.pages = []
        self.current_commands = []
        
    def add_page(self):
        if self.current_commands:
            self.pages.append("\n".join(self.current_commands))
            self.current_commands = []
            
    def add_header(self, text, y=750):
        self.current_commands.append("BT")
        self.current_commands.append("/F2 20 Tf")
        self.current_commands.append("0.45 0.25 0.85 rg")
        self.current_commands.append(f"50 {y} Td")
        self.current_commands.append(f"({self.escape(text)}) Tj")
        self.current_commands.append("ET")
        self.current_commands.append("0.85 0.85 0.90 RG")
        self.current_commands.append("1 w")
        self.current_commands.append(f"50 {y - 8} m 562 {y - 8} l S")

    def add_subheader(self, text, y):
        self.current_commands.append("BT")
        self.current_commands.append("/F2 13 Tf")
        self.current_commands.append("0.15 0.15 0.25 rg")
        self.current_commands.append(f"50 {y} Td")
        self.current_commands.append(f"({self.escape(text)}) Tj")
        self.current_commands.append("ET")

    def add_text(self, text, x, y, size=10, bold=False, color=(0.2, 0.2, 0.2)):
        font = "/F2" if bold else "/F1"
        self.current_commands.append("BT")
        self.current_commands.append(f"{font} {size} Tf")
        self.current_commands.append(f"{color[0]} {color[1]} {color[2]} rg")
        self.current_commands.append(f"{x} {y} Td")
        self.current_commands.append(f"({self.escape(text)}) Tj")
        self.current_commands.append("ET")

    def add_box(self, x, y, w, h, fill_color=(0.95, 0.95, 0.98), stroke_color=(0.8, 0.8, 0.9)):
        self.current_commands.append(f"{fill_color[0]} {fill_color[1]} {fill_color[2]} rg")
        self.current_commands.append(f"{stroke_color[0]} {stroke_color[1]} {stroke_color[2]} RG")
        self.current_commands.append("1 w")
        self.current_commands.append(f"{x} {y} {w} {h} re B")

    def escape(self, text):
        clean = text.encode('ascii', 'replace').decode('ascii')
        return clean.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

    def save(self, filename):
        if self.current_commands:
            self.pages.append("\n".join(self.current_commands))
            
        objects = []
        objects.append("1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj")
        
        page_refs = [f"{i+3} 0 R" for i in range(len(self.pages))]
        objects.append(f"2 0 obj\n<< /Type /Pages /Kids [{' '.join(page_refs)}] /Count {len(self.pages)} >>\nendobj")
        
        font_obj = (
            "<< /Font <<\n"
            "/F1 << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\n"
            "/F2 << /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>\n"
            "/F3 << /Type /Font /Subtype /Type1 /BaseFont /Courier >>\n"
            ">> >>"
        )
        
        content_start_obj_num = 3 + len(self.pages)
        
        for i, page_cmd in enumerate(self.pages):
            page_obj_num = 3 + i
            content_obj_num = content_start_obj_num + i
            objects.append(
                f"{page_obj_num} 0 obj\n"
                f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources {font_obj} /Contents {content_obj_num} 0 R >>\n"
                f"endobj"
            )
            
        for i, page_cmd in enumerate(self.pages):
            content_obj_num = content_start_obj_num + i
            stream_bytes = page_cmd.encode('ascii', 'replace')
            objects.append(
                f"{content_obj_num} 0 obj\n"
                f"<< /Length {len(stream_bytes)} >>\n"
                f"stream\n"
                f"{page_cmd}\n"
                f"endstream\n"
                f"endobj"
            )

        pdf_header = "%PDF-1.4\n"
        offsets = []
        current_offset = len(pdf_header)
        
        body_str = ""
        for obj in objects:
            offsets.append(current_offset)
            body_str += obj + "\n"
            current_offset = len(pdf_header) + len(body_str)
            
        xref_offset = current_offset
        xref_str = f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n"
        for off in offsets:
            xref_str += f"{off:010d} 00000 n \n"
            
        trailer_str = f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n"
        
        with open(filename, "wb") as f:
            f.write(pdf_header.encode('ascii'))
            f.write(body_str.encode('ascii'))
            f.write(xref_str.encode('ascii'))
            f.write(trailer_str.encode('ascii'))
            
        print(f"Presentation PDF successfully created at: {filename}")

def build_pdf():
    pdf = SimplePDFWriter()
    
    # -------------------------------------------------------------
    # PAGE 1: TITLE & EXECUTIVE SUMMARY
    # -------------------------------------------------------------
    pdf.add_box(40, 680, 532, 85, fill_color=(0.06, 0.06, 0.12), stroke_color=(0.54, 0.36, 0.96))
    pdf.add_text("PRICESENSE INTELLIGENCE ENGINE", 60, 735, size=21, bold=True, color=(0.95, 0.95, 1.0))
    pdf.add_text("Real-Time Quick Commerce Pricing Matrix & Hyperlocal Analytics", 60, 700, size=11, bold=False, color=(0.75, 0.75, 0.95))
    
    y = 650
    pdf.add_subheader("1. Executive Summary & Problem Overview", y)
    y -= 20
    text_p1 = [
        "PriceSense is a real-time competitive pricing intelligence engine designed for India's rapidly growing",
        "quick-commerce ecosystem (Blinkit, Zepto, Swiggy Instamart, and BigBasket). Quick-commerce platforms",
        "dynamically alter item prices, stock availability, and discounts based on hyperlocal dark stores and GPS coordinates.",
        "",
        "Key Challenges Addressed by PriceSense:",
        "* Manual Price Hunting: Consumers and analysts waste time opening multiple apps to check item prices.",
        "* Hyperlocal Variance: Prices and stock depend heavily on pincodes (e.g. Mumbai vs. Delhi vs. Bengaluru).",
        "* Anti-Bot Protection: Platforms use heavy obfuscation, dynamic DOM classes, and Cloudflare/Kasada blocks.",
        "* Price Transparency: Lack of unified analytics comparing market minimums, averages, and potential savings."
    ]
    for line in text_p1:
        if line.startswith("*"):
            pdf.add_text(line, 65, y, size=10, bold=False)
        elif line.endswith(":"):
            pdf.add_text(line, 50, y, size=10, bold=True)
        else:
            pdf.add_text(line, 50, y, size=10, bold=False)
        y -= 15
        
    y -= 10
    pdf.add_subheader("2. System Architecture & High-Level Flow", y)
    y -= 25
    
    pdf.add_box(50, y - 110, 512, 120, fill_color=(0.96, 0.96, 0.98), stroke_color=(0.8, 0.8, 0.9))
    pdf.add_text("[User Dashboard UI]  -->  GET /search?q=query&location=city  -->  [Flask REST API app.py]", 65, y - 20, size=9, bold=True, color=(0.2, 0.2, 0.5))
    pdf.add_text("                                                                        |", 65, y - 35, size=9, bold=True, color=(0.4, 0.4, 0.4))
    pdf.add_text("                                                                        v", 65, y - 50, size=9, bold=True, color=(0.4, 0.4, 0.4))
    pdf.add_text("[Playwright Engine] <-- Geolocation Context Injection <-- [LOCATIONS Matrix (Lat/Lng/Pincode)]", 65, y - 65, size=9, bold=True, color=(0.5, 0.2, 0.5))
    pdf.add_text("        |--> Parallel Page Tabs: Blinkit | Zepto | Swiggy Instamart | BigBasket", 65, y - 80, size=9, bold=True, color=(0.1, 0.5, 0.3))
    pdf.add_text("        |--> Extraction: DOM Traversal + __NEXT_DATA__ JSON State Parsing --> Aggregator", 65, y - 95, size=9, bold=True, color=(0.2, 0.2, 0.2))

    y -= 140
    pdf.add_subheader("3. Key Technologies Used", y)
    y -= 20
    techs = [
        ("Playwright (Python)", "Automated browser context control, stealth launch, and headless/headful rendering."),
        ("Flask (Python Backend)", "Lightweight REST API serving search routes and rendering single-page Web UI."),
        ("Chart.js & Inter UI", "Interactive analytics bar chart, dynamic tooltip callbacks, and modern glassmorphic dashboard."),
        ("Hyperlocal GPS Spoofing", "Injecting latitude/longitude coordinates & permissions into browser contexts per city.")
    ]
    for title, desc in techs:
        pdf.add_text(f"* {title}: ", 60, y, size=10, bold=True)
        pdf.add_text(desc, 180, y, size=10, bold=False)
        y -= 16

    pdf.add_text("PriceSense Technical Documentation --- Page 1 of 3", 220, 30, size=9, color=(0.5, 0.5, 0.5))
    pdf.add_page()
    
    # -------------------------------------------------------------
    # PAGE 2: CODE ANALYSIS & IMPLEMENTATION DETAILS
    # -------------------------------------------------------------
    pdf.add_header("Code Implementation & Module Breakdown")
    y = 710
    
    pdf.add_subheader("4. Flask Backend API (app.py)", y)
    y -= 20
    pdf.add_text("The app.py module acts as the web server entry point, handling incoming requests from the frontend:", 50, y, size=10)
    y -= 18
    
    pdf.add_box(50, y - 75, 512, 80, fill_color=(0.05, 0.05, 0.08), stroke_color=(0.3, 0.3, 0.4))
    pdf.add_text("@app.route('/search')", 60, y - 20, size=9, bold=True, color=(0.4, 0.8, 1.0))
    pdf.add_text("def search():", 60, y - 35, size=9, bold=True, color=(0.9, 0.9, 0.9))
    pdf.add_text("    query = request.args.get('q', '').strip()", 60, y - 50, size=9, color=(0.7, 0.9, 0.7))
    pdf.add_text("    location = request.args.get('location', 'mumbai').strip()", 60, y - 65, size=9, color=(0.7, 0.9, 0.7))
    pdf.add_text("    products = scrape_prices(query, location=location)", 60, y - 80, size=9, color=(1.0, 0.8, 0.4))
    
    y -= 95
    pdf.add_subheader("5. Scraper Engine (scraper.py)", y)
    y -= 20
    
    scraper_sections = [
        ("a) Hyperlocal Location Mapping (LOCATIONS)", [
            "We define a dictionary mapping target Indian cities (Mumbai, Delhi, Bengaluru, Gurgaon, etc.) to",
            "exact GPS latitude, longitude, and pincodes (e.g. Mumbai 400001 -> lat: 19.0760, lng: 72.8777).",
            "Playwright browser contexts are initialized with permissions=['geolocation'] and mock lat/lng."
        ]),
        ("b) Browser Context & Page Isolation (run_scraper)", [
            "To prevent cookies, local storage, or navigation errors from cross-contaminating scrapers,",
            "each platform function (scrape_blinkit, scrape_zepto, scrape_instamart, scrape_bigbasket) is",
            "executed in its own dedicated browser page tab (context.new_page()) and closed immediately after."
        ]),
        ("c) Dual-Layer Extraction: DOM Fallback + __NEXT_DATA__ JSON Parsing", [
            "Modern Next.js / React apps obscure class names. PriceSense uses a two-tier extraction system:",
            "1. DOM Selector Traversal: Iterates through product card & title selectors.",
            "2. JSON State Payload Parsing: Scans <script id='__NEXT_DATA__'> for raw product JSON payloads."
        ]),
        ("d) Query Relevance Filtering (is_relevant_product)", [
            "Prevents unrelated items (e.g. cake rusks when searching 'amul milk') by matching query tokens.",
            "Checks direct substring inclusion and token set overlap before adding candidates to results."
        ]),
        ("e) Product Matching & Price Estimation Engine", [
            "find_best_match uses SequenceMatcher (fuzzy ratio) and pack size extraction (100g vs 500ml).",
            "estimate_missing_prices calculates average market price from at least 2 real live price points."
        ])
    ]
    
    for title, desc_lines in scraper_sections:
        pdf.add_text(title, 55, y, size=10, bold=True, color=(0.2, 0.2, 0.5))
        y -= 14
        for line in desc_lines:
            pdf.add_text(line, 65, y, size=9, color=(0.25, 0.25, 0.25))
            y -= 13
        y -= 5

    pdf.add_text("PriceSense Technical Documentation --- Page 2 of 3", 220, 30, size=9, color=(0.5, 0.5, 0.5))
    pdf.add_page()

    # -------------------------------------------------------------
    # PAGE 3: FRONTEND UI & PRESENTATION GUIDELINES
    # -------------------------------------------------------------
    pdf.add_header("Frontend Architecture & Presentation Guide")
    y = 710

    pdf.add_subheader("6. Frontend UI & Analytics Dashboard (templates/index.html & style.css)", y)
    y -= 20
    
    fe_features = [
        ("Executive KPI Summary Cards", "Displays 4 real-time metrics: Best Value Platform, Minimum Live Price, Market Average, and Maximum Monetary Savings."),
        ("Interactive Quick Search Pills", "One-click popular search chips (Amul Milk, Amul Butter, Dairy Milk, Brown Bread, Eggs, Coca Cola)."),
        ("Source-Aware Price Pills", "Distinguishes directly extracted LIVE prices (Green Pill) from ESTIMATED averages (Amber Pill)."),
        ("Responsive Platform Matrix", "Full-width table layout with explicit column constraints preventing badge clipping or awkward text wraps."),
        ("Chart.js Analytics Canvas", "Bar chart displaying price comparisons across platforms with full product names rendered in hover tooltips.")
    ]
    for title, desc in fe_features:
        pdf.add_text(f"* {title}: ", 60, y, size=10, bold=True)
        pdf.add_text(desc, 200, y, size=9, bold=False)
        y -= 16

    y -= 10
    pdf.add_subheader("7. Step-by-Step Presentation & Demo Script", y)
    y -= 20

    presentation_steps = [
        ("Step 1: Introduction", "Introduce PriceSense as a real-time price intelligence engine solving quick-commerce price opacity."),
        ("Step 2: Location Selection", "Select 'Mumbai (400001)' or 'Delhi (110001)' from the Location Dropdown to demonstrate GPS spoofing."),
        ("Step 3: Live Query Search", "Click 'Amul Milk' quick pill or type a product. Point out the terminal animation logging browser context setup."),
        ("Step 4: Real Browser Execution", "Show the live Chromium window opening and loading Blinkit, Zepto, Swiggy Instamart, and BigBasket tabs."),
        ("Step 5: KPI & Table Matrix", "Highlight the Best Value Platform badge, live price pills, and potential savings card."),
        ("Step 6: Price Analytics Chart", "Hover over the bar chart to show full product titles and cross-platform price variance.")
    ]

    for step, details in presentation_steps:
        pdf.add_box(50, y - 22, 512, 26, fill_color=(0.97, 0.97, 0.99), stroke_color=(0.85, 0.85, 0.95))
        pdf.add_text(step, 60, y - 16, size=9, bold=True, color=(0.4, 0.2, 0.8))
        pdf.add_text(details, 180, y - 16, size=9, bold=False, color=(0.2, 0.2, 0.2))
        y -= 32

    y -= 15
    pdf.add_subheader("8. Conclusion & Future Roadmap", y)
    y -= 18
    roadmap = [
        "* Historical Price Tracking: Storing price snapshots in SQLite/PostgreSQL to render 30-day price trend lines.",
        "* Cart Optimization Engine: Allowing users to add a 10-item grocery basket and calculating the cheapest total store.",
        "* Automated Stock Alerts: Sending Telegram/Email notifications when high-demand items come back in stock."
    ]
    for r in roadmap:
        pdf.add_text(r, 60, y, size=9, bold=False)
        y -= 15

    pdf.add_text("PriceSense Technical Documentation --- Page 3 of 3", 220, 30, size=9, color=(0.5, 0.5, 0.5))

    output_filename = "/Users/omkar/Desktop/DONEEEEE/PriceSense/PriceSense_Project_Presentation.pdf"
    pdf.save(output_filename)

if __name__ == "__main__":
    build_pdf()
