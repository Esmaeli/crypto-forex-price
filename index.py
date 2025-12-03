# -*- coding: utf-8 -*-
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import concurrent.futures
import time

# --- Configuration ---
base_url = 'https://arzdigital.com/coins/'
urls_to_scrape = [base_url]  # Page 1
urls_to_scrape.extend([f"{base_url}page-{i}/" for i in range(2, 11)])  # Pages 2 to 10
output_filename = 'arzdigital_data.txt'
MAX_WORKERS = 10

# --- Helper function to process a single page using Selenium ---
def fetch_and_parse_page(url, page_num):
    print(f"[Thread-{page_num}] Fetching page {page_num}: {url}...")
    page_coin_data = []

    # Selenium headless setup
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")

    driver = webdriver.Chrome(options=options)
    try:
        driver.get(url)

        # Wait until table rows are loaded
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "tr.arz-coin-tr"))
        )

        coin_rows = driver.find_elements(By.CSS_SELECTOR, "tr.arz-coin-tr")
        for row in coin_rows:
            try:
                symbol = row.get_attribute("data-symbol") or "N/A"

                rank_td = row.find_element(By.CSS_SELECTOR, "td.arz-coin-table__number-td span")
                rank = rank_td.text.strip() if rank_td else "N/A"

                name_td = row.find_element(By.CSS_SELECTOR, "td.arz-coin-table__name-td")
                name_link = name_td.find_elements(By.TAG_NAME, "a")
                name = name_link[0].text.strip() if name_link else row.get_attribute("data-name") or "N/A"

                logo_img_tag = name_td.find_element(By.CSS_SELECTOR, "img.arz-coin-image")
                logo_url = logo_img_tag.get_attribute("data-src") if logo_img_tag else "N/A"

                price_td = row.find_element(By.CSS_SELECTOR, "td.arz-coin-table__price-td span")
                price_usd = price_td.text.strip() if price_td else "N/A"

                rial_price_td = row.find_element(By.CSS_SELECTOR, "td.arz-coin-table__rial-price-td span span")
                price_toman = rial_price_td.text.strip() if rial_price_td else "N/A"

                marketcap_td = row.find_element(By.CSS_SELECTOR, "td.arz-coin-table__marketcap-td")
                marketcap_usd_span = marketcap_td.find_element(By.CSS_SELECTOR, "span[dir='auto']")
                marketcap_usd = marketcap_usd_span.text.strip() if marketcap_usd_span else "N/A"
                marketcap_toman_span = marketcap_td.find_elements(By.CSS_SELECTOR, "span.arz-value-unit")
                marketcap_toman = marketcap_toman_span[0].text.strip() if marketcap_toman_span else "N/A"

                volume_td = row.find_element(By.CSS_SELECTOR, "td.arz-coin-table__volume-td")
                volume_usd_span = volume_td.find_element(By.CSS_SELECTOR, "span[dir='auto']")
                volume_usd = volume_usd_span.text.strip() if volume_usd_span else "N/A"
                volume_toman_span = volume_td.find_elements(By.CSS_SELECTOR, "span.arz-value-unit")
                volume_toman = volume_toman_span[0].text.strip() if volume_toman_span else "N/A"

                def get_change_text(cell_selector):
                    try:
                        span = row.find_element(By.CSS_SELECTOR, cell_selector)
                        text = span.text.strip()
                        classes = span.get_attribute("class").split()
                        if "arz-positive" in classes: return f"+{text}"
                        elif "arz-negative" in classes: return f"-{text}" if not text.startswith("-") else text
                        else: return text
                    except:
                        return "N/A"

                daily_change = get_change_text("td.arz-coin-table__daily-swing-td span")
                weekly_change = get_change_text("td.arz-coin-table__weekly-swing-td span")

                coin_data = {
                    'Rank': rank, 'Name': name, 'Slug': symbol, 'Price_USD': price_usd,
                    'Price_Toman': price_toman, 'Total_Market_USD': marketcap_usd,
                    'Total_Market_Toman': marketcap_toman, 'Daily_Market_USD': volume_usd,
                    'Daily_Market_Toman': volume_toman, 'Daily_Positive_Negative': daily_change,
                    'Weekly_Positive_Negative': weekly_change,
                    'Logo': logo_url
                }
                page_coin_data.append(coin_data)
            except Exception as e:
                print(f"[Thread-{page_num}] Error processing row: {e}. Skipping...")
                continue

        print(f"[Thread-{page_num}] Finished processing page {page_num} ({len(page_coin_data)} coins).")
        return (page_num, page_coin_data)

    except Exception as e:
        print(f"[Thread-{page_num}] Error fetching page {page_num}: {e}")
        return (page_num, [])

    finally:
        driver.quit()


# --- Main Execution Logic ---
start_time = time.time()
page_results_list = []
futures = {}

with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
    for i, url in enumerate(urls_to_scrape, 1):
        future = executor.submit(fetch_and_parse_page, url, i)
        futures[future] = i

    for future in concurrent.futures.as_completed(futures):
        page_num = futures[future]
        try:
            result_tuple = future.result()
            if result_tuple and isinstance(result_tuple, tuple) and len(result_tuple) == 2:
                page_results_list.append(result_tuple)
        except Exception as exc:
            print(f"[Thread-{page_num}] Exception: {exc}")

# Sort by page number
page_results_list.sort(key=lambda item: item[0])

# Flatten list
all_coins_data = []
for page_num, coin_list in page_results_list:
    all_coins_data.extend(coin_list)

# Write to file
with open(output_filename, 'w', encoding='utf-8') as f:
    for i, coin in enumerate(all_coins_data):
        f.write(f"Rank: {coin['Rank']}\n")
        f.write(f"Name: {coin['Name']}\n")
        f.write(f"Slug: {coin['Slug']}\n")
        f.write(f"Price_USD: {coin['Price_USD']}\n")
        f.write(f"Price_Toman: {coin['Price_Toman']}\n")
        f.write(f"Total_Market_USD: {coin['Total_Market_USD']}\n")
        f.write(f"Total_Market_Toman: {coin['Total_Market_Toman']}\n")
        f.write(f"Daily_Market_USD: {coin['Daily_Market_USD']}\n")
        f.write(f"Daily_Market_Toman: {coin['Daily_Market_Toman']}\n")
        f.write(f"Daily_Positive_Negative: {coin['Daily_Positive_Negative']}\n")
        f.write(f"Weekly_Positive_Negative: {coin['Weekly_Positive_Negative']}\n")
        f.write(f"Logo: {coin['Logo']}\n")
        if i < len(all_coins_data) - 1:
            f.write("***\n***\n***\n")

end_time = time.time()
print(f"Scraping finished in {end_time - start_time:.2f} seconds. Total coins: {len(all_coins_data)}")
