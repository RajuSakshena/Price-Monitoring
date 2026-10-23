# Consumer Affairs Wholesale Price Scraper

Downloads the official Department of Consumer Affairs daily average wholesale-price report and saves parsed data as JSON and CSV.

**Source:** https://fcainfoweb.nic.in/Reports/DB/DBprices_W.aspx

## Windows setup

1. Install Python 3.11 or newer from https://www.python.org/downloads/ and enable **Add Python to PATH**.
2. Extract this ZIP to a normal folder, for example `C:\\Projects\\wholesale_price_scraper`.
3. Double-click `run_windows.bat`, or open a terminal in the folder and run:

```powershell
py -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python main.py
```

## Output files

- `output/wholesale_prices_latest.json` — latest successful scrape.
- `output/wholesale_prices_latest.csv` — latest successful scrape in spreadsheet-friendly format.
- `output/wholesale_prices_YYYY-MM-DD.json` — dated JSON snapshot based on the computer's local date.
- `output/last_response.html` — raw HTML returned by the website for debugging.
- `output/debug.html` — saved if the parser cannot identify price rows.

## Daily automation on Windows

After the first successful run:

1. Open **Task Scheduler**.
2. Select **Create Basic Task** and name it `Consumer Affairs Wholesale Scraper`.
3. Choose **Daily** and set a time after the government report is usually updated.
4. For **Start a program**, select the full path to `python.exe` inside this project's `.venv\\Scripts\\python.exe`.
5. Set **Add arguments** to the full path of `main.py` in this folder.
6. Set **Start in** to the project folder.
7. Save and use **Run** to test it.

## Important notes

- This scraper reads the public report page; it does not bypass login or access controls.
- Government website HTML can change. If parsing fails, check `output/last_response.html` and `output/debug.html` before changing selectors.
- The source page is an all-India daily average wholesale report, not the AGMARKNET market-wise mandi dataset.
- This package does not yet write to Neon/PostgreSQL. Add database insertion only after confirming the saved rows and field meanings.
