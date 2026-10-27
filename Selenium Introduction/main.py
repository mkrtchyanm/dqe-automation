import time
import os
import pandas as pd

from selenium import webdriver
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException


import os
import re
import time
import pandas as pd

from selenium import webdriver
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException


class SeleniumWebDriverContextManager:
    def __init__(self, headless: bool = True, window_size: str = "1920,1080"):
        self.headless = headless
        self.window_size = window_size
        self.driver: WebDriver | None = None

    def __enter__(self) -> WebDriver:
        options = webdriver.ChromeOptions()
        if self.headless:
            options.add_argument("--headless=new")
        options.add_argument(f"--window-size={self.window_size}")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")

        self.driver = webdriver.Chrome(options=options)
        return self.driver

    def __exit__(self, exc_type, exc_value, traceback):
        if self.driver:
            try:
                self.driver.quit()
            except Exception as e:
                print(f"[WARNING] Error while closing WebDriver: {e}")


def extract_table_data(driver: WebDriver, output_csv_path: str) -> pd.DataFrame:
    print("\n--- Starting Table Data Extraction ---")
    try:
        table_element = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.XPATH, "//*[@class='table']"))
        )
        print("[INFO] Located table container using By.XPATH.")

        columns = table_element.find_elements(By.CSS_SELECTOR, ".y-column")
        if not columns:
            raise NoSuchElementException("No columns with class 'y-column' found in table.")
        print(f"[INFO] Found {len(columns)} table columns using By.CSS_SELECTOR.")

        table_data = {}
        for col_idx, col in enumerate(columns):
            header_elem = col.find_element(By.ID, "header")
            header_text = header_elem.text.strip()
            print(f"[INFO] Column {col_idx + 1} header found using By.ID: '{header_text}'")

            cell_blocks = col.find_elements(By.CLASS_NAME, "column-cell")
            ordered_cell_values = []

            for cb in cell_blocks:
                try:
                    gparent = cb.find_element(By.XPATH, "../..")
                    if gparent.get_attribute("id") == "header":
                        continue

                    gp_tr = gparent.get_attribute("transform") or ""
                    cb_tr = cb.get_attribute("transform") or ""
                    gp_match = re.search(r'translate\(\s*[\d\.\-]+\s*,\s*([\d\.\-]+)\s*\)', gp_tr)
                    cb_match = re.search(r'translate\(\s*[\d\.\-]+\s*,\s*([\d\.\-]+)\s*\)', cb_tr)

                    gp_y = float(gp_match.group(1)) if gp_match else 0.0
                    cb_y = float(cb_match.group(1)) if cb_match else 0.0
                    total_y = gp_y + cb_y

                    text_elem = cb.find_element(By.CLASS_NAME, "cell-text")
                    ordered_cell_values.append((total_y, text_elem.text.strip()))
                except NoSuchElementException:
                    continue

            # Sort values by their vertical display position (Y coordinate)
            ordered_cell_values.sort(key=lambda item: item[0])
            column_values = [val for _, val in ordered_cell_values]
            table_data[header_text] = column_values

        df_table = pd.DataFrame(table_data)
        df_table.to_csv(output_csv_path, index=False)
        print(f"[SUCCESS] Table extracted successfully ({len(df_table)} rows) and saved to: {output_csv_path}")
        return df_table

    except (TimeoutException, NoSuchElementException) as e:
        print(f"[ERROR] Failed to extract table: {e}")
        raise


def extract_doughnut_slice_data(chart_element) -> list[dict]:
    slice_data = []
    slice_labels = chart_element.find_elements(By.CSS_SELECTOR, "text.slicetext[data-notex='1']")
    for label in slice_labels:
        tspans = label.find_elements(By.TAG_NAME, "tspan")
        if len(tspans) >= 2:
            category = tspans[0].text.strip()
            value = tspans[1].text.strip()
            slice_data.append({"Facility Type": category, "Min Average Time Spent": value})
        elif len(tspans) == 1:
            slice_data.append({"Facility Type": tspans[0].text.strip(), "Min Average Time Spent": ""})
    return slice_data


def capture_chart_screenshot(driver: WebDriver, file_path: str):
    try:
        doughnut_element = driver.find_element(By.CLASS_NAME, "pielayer")
        size = doughnut_element.size
        if size.get("width", 0) > 0 and size.get("height", 0) > 0:
            doughnut_element.screenshot(file_path)
            return
    except Exception:
        pass

    try:
        plot_div = driver.find_element(By.CLASS_NAME, "plotly-graph-div")
        plot_div.screenshot(file_path)
    except Exception:
        driver.save_screenshot(file_path)


def interact_with_doughnut_chart(driver: WebDriver, output_dir: str):
    print("\n--- Starting Doughnut Chart Interaction ---")
    try:
        doughnut_element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "pielayer"))
        )
        print("[INFO] Doughnut chart layer (.pielayer) found.")

        screenshot0_path = os.path.join(output_dir, "screenshot0.png")
        doughnut0_csv_path = os.path.join(output_dir, "doughnut0.csv")

        capture_chart_screenshot(driver, screenshot0_path)
        initial_data = extract_doughnut_slice_data(doughnut_element)
        pd.DataFrame(initial_data, columns=["Facility Type", "Min Average Time Spent"]).to_csv(
            doughnut0_csv_path, index=False
        )
        print(f"[SUCCESS] Saved initial state: {screenshot0_path} and {doughnut0_csv_path} ({len(initial_data)} slices)")

        scrollbox = driver.find_element(By.CLASS_NAME, "scrollbox")
        legend_traces = scrollbox.find_elements(By.CLASS_NAME, "traces")
        num_traces = len(legend_traces)
        print(f"[INFO] Found {num_traces} legend filter traces.")

        # Iterate through each filter option
        for idx in range(num_traces):
            stage_num = idx + 1
            screenshot_path = os.path.join(output_dir, f"screenshot{stage_num}.png")
            csv_path = os.path.join(output_dir, f"doughnut{stage_num}.csv")

            scrollbox = driver.find_element(By.CLASS_NAME, "scrollbox")
            traces = scrollbox.find_elements(By.CLASS_NAME, "traces")
            filter_item = traces[idx]
            filter_name = filter_item.text.strip()

            print(f"[INFO] Applying filter [{stage_num}/{num_traces}]: clicking '{filter_name}'")
            filter_item.click()

            time.sleep(1)

            doughnut_element = driver.find_element(By.CLASS_NAME, "pielayer")
            capture_chart_screenshot(driver, screenshot_path)
            slice_data = extract_doughnut_slice_data(doughnut_element)

            if not slice_data:
                print(f"[INFO] Edge case handled at stage {stage_num}: all filters unselected (0 visible slices).")
                df_empty = pd.DataFrame(columns=["Facility Type", "Min Average Time Spent"])
                df_empty.to_csv(csv_path, index=False)
            else:
                pd.DataFrame(slice_data, columns=["Facility Type", "Min Average Time Spent"]).to_csv(
                    csv_path, index=False
                )

            print(f"[SUCCESS] Saved stage {stage_num}: {screenshot_path} and {csv_path} ({len(slice_data)} slices)")

    except (TimeoutException, NoSuchElementException) as e:
        print(f"[ERROR] Exception during doughnut chart interaction: {e}")
        raise


if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.abspath(__file__))
    html_report_path = os.path.join(base_dir, "report.html")

    if not os.path.exists(html_report_path):
        raise FileNotFoundError(f"HTML report not found at: {html_report_path}")

    with SeleniumWebDriverContextManager(headless=True) as driver:
        file_url = f"file:///{html_report_path.replace(os.sep, '/')}"
        print(f"[INFO] Opening report: {file_url}")
        driver.get(file_url)

        # 1. Table Interaction , so it  Extracts content to table.csv
        table_csv_file = os.path.join(base_dir, "table.csv")
        extract_table_data(driver, table_csv_file)

        # 2. Doughnut Chart Interaction,screenshots & doughnut0..N.csv
        interact_with_doughnut_chart(driver, base_dir)

    print("\n[ALL TASKS COMPLETED SUCCESSFULLY]")
