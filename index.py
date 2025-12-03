# -*- coding: utf-8 -*-
# Import necessary libraries
import requests                 # To send HTTP requests
from bs4 import BeautifulSoup     # To parse HTML
import concurrent.futures   # For running tasks concurrently (multithreading)
import time                     # To measure execution time

# --- Configuration ---
base_url = 'https://arzdigital.com/coins/'
# Create a list of URLs for pages 1 to 10
urls_to_scrape = [base_url] # Page 1
urls_to_scrape.extend([f"{base_url}page-{i}/" for i in range(2, 11)]) # Pages 2 to 10

# Output filename for all extracted data
output_filename = 'arzdigital_data.txt'
# Number of concurrent workers (threads) - set to 10 for 10 pages
MAX_WORKERS = 10

# --- Helper function to process a single page ---
def fetch_and_parse_page(url, page_num):
    """Downloads, parses a single page URL, extracts coin data including logo, and returns (page_num, list_of_coins)."""
    print(f"[Thread-{page_num}] Fetching page {page_num}: {url}...")
    page_coin_data = [] # Data for this specific page
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        # Use a session object for potential connection reuse benefits
        with requests.Session() as session:
            response = session.get(url, headers=headers, timeout=20)
            response.raise_for_status()
            html_content = response.text

        soup = BeautifulSoup(html_content, 'html.parser')
        coin_rows = soup.find_all('tr', class_='arz-coin-tr')

        if not coin_rows:
            return (page_num, page_coin_data) # Return page number and empty list

        # Helper function to safely extract text from a tag
        def get_text_safe(element):
            return element.get_text(strip=True) if element else 'N/A'

        # Helper function to extract change text and add sign
        def get_change_text(element):
            if not element: return 'N/A'
            text = element.get_text(strip=True)
            classes = element.get('class', [])
            if 'arz-positive' in classes: return f"+{text}"
            elif 'arz-negative' in classes: return f"-{text}" if not text.startswith('-') else text
            else: return text

        for row in coin_rows:
            try:
                symbol = row.get('data-symbol', 'N/A')

                rank_td = row.find('td', class_='arz-coin-table__number-td')
                rank = get_text_safe(rank_td.find('span'))

                name_td = row.find('td', class_='arz-coin-table__name-td')
                name_link = name_td.find('a')
                name = get_text_safe(name_link.find('span')) if name_link else row.get('data-name', 'N/A')
                # Find the image tag within the name cell and get data-src
                logo_img_tag = name_td.find('img', class_='arz-coin-image')
                logo_url = logo_img_tag.get('data-src', 'N/A') if logo_img_tag else 'N/A'

                price_td = row.find('td', class_='arz-coin-table__price-td')
                price_usd = get_text_safe(price_td.find('span'))

                rial_price_td = row.find('td', class_='arz-coin-table__rial-price-td')
                rial_nested_span = rial_price_td.find('span').find('span') if rial_price_td and rial_price_td.find('span') else None
                price_toman = get_text_safe(rial_nested_span)

                marketcap_td = row.find('td', class_='arz-coin-table__marketcap-td')
                marketcap_usd = get_text_safe(marketcap_td.find('span', {'dir': 'auto'}))
                marketcap_toman = get_text_safe(marketcap_td.find('span', class_='arz-value-unit'))

                volume_td = row.find('td', class_='arz-coin-table__volume-td')
                volume_usd = get_text_safe(volume_td.find('span', {'dir': 'auto'}))
                volume_toman = get_text_safe(volume_td.find('span', class_='arz-value-unit'))

                daily_swing_td = row.find('td', class_='arz-coin-table__daily-swing-td')
                daily_change_span = daily_swing_td.find('span') if daily_swing_td else None
                daily_change = get_change_text(daily_change_span)

                weekly_swing_td = row.find('td', class_='arz-coin-table__weekly-swing-td')
                weekly_change_span = weekly_swing_td.find('span') if weekly_swing_td else None
                weekly_change = get_change_text(weekly_change_span)

                # Add all data including the new logo URL to the dictionary
                coin_data = {
                    'Rank': rank, 'Name': name, 'Slug': symbol, 'Price_USD': price_usd,
                    'Price_Toman': price_toman, 'Total_Market_USD': marketcap_usd,
                    'Total_Market_Toman': marketcap_toman, 'Daily_Market_USD': volume_usd,
                    'Daily_Market_Toman': volume_toman, 'Daily_Positive_Negative': daily_change,
                    'Weekly_Positive_Negative': weekly_change,
                    'Logo': logo_url # Added logo URL here
                }
                page_coin_data.append(coin_data)
            except AttributeError as e:
                print(f"[Thread-{page_num}] Error processing a row on page {page_num}: {e}. Skipping row.")
                continue

        print(f"[Thread-{page_num}] Finished processing page {page_num} ({len(page_coin_data)} coins).")
        return (page_num, page_coin_data) # Return tuple (page_number, list_of_data)

    except requests.exceptions.RequestException as e:
        print(f"[Thread-{page_num}] Error downloading page {page_num} ({url}): {e}.")
        return (page_num, []) # Return page number and empty list on download error
    except Exception as e:
        print(f"[Thread-{page_num}] An unexpected error occurred processing page {page_num} ({url}): {e}.")
        return (page_num, []) # Return page number and empty list on other errors

# --- Main Execution Logic ---
start_time = time.time() # Record start time

print("Starting concurrent scraping process...")
# List to store results from threads temporarily, as tuples (page_num, coin_list)
page_results_list = []
futures = {}

# Use ThreadPoolExecutor to run tasks concurrently
with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
    # Submit each page fetch task to the executor
    for i, url in enumerate(urls_to_scrape, 1):
        future = executor.submit(fetch_and_parse_page, url, i)
        futures[future] = i # Store page number against future

    # Process results as they complete
    print("Waiting for page processing tasks to complete...")
    processed_tasks = 0
    for future in concurrent.futures.as_completed(futures):
        page_num = futures[future]
        try:
            # result is now a tuple: (page_num_from_func, list_of_coins)
            result_tuple = future.result()
            if result_tuple and isinstance(result_tuple, tuple) and len(result_tuple) == 2:
                # Store the entire tuple (page_num, coin_list)
                page_results_list.append(result_tuple)
            else:
                 print(f"Processing for Page {page_num} returned unexpected data format.")
            processed_tasks += 1
        except Exception as exc:
            # Catch exceptions that might occur when calling future.result() itself
            print(f'Page {page_num} generated an exception upon result retrieval: {exc}')
            processed_tasks += 1

print(f"\nFinished processing all submitted tasks ({processed_tasks}).")

# --- Sort the results based on page number ---
print("Sorting results by page number...")
page_results_list.sort(key=lambda item: item[0]) # Sort based on the first element (page_num)

# --- Flatten the sorted results into the final list ---
print("Constructing final ordered list...")
all_coins_data = []
for page_num, coin_list in page_results_list:
    if coin_list: # Make sure the list is not empty or None before extending
        all_coins_data.extend(coin_list)
    print(f"Adding {len(coin_list)} coins from sorted Page {page_num}.")


print(f"\nTotal coins extracted in order: {len(all_coins_data)}.")

# --- Write collected data to file ---
print(f"Writing all extracted data to {output_filename}...")
try:
    with open(output_filename, 'w', encoding='utf-8') as f:
        for i, coin in enumerate(all_coins_data):
            # Write data in the requested format
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
            f.write(f"Logo: {coin['Logo']}\n") # Added the logo URL line here
            if i < len(all_coins_data) - 1:
                 f.write("***\n***\n***\n") # Record separator
    print("Writing data to file completed successfully.")
except IOError as e:
    print(f"Error writing data to output file: {e}")
except Exception as e:
    print(f"An unexpected error occurred during file writing: {e}")

end_time = time.time() # Record end time
print(f"Script execution finished in {end_time - start_time:.2f} seconds.")
