import requests
from bs4 import BeautifulSoup

def fetch_currency_prices(url):
    """
    Fetches and parses currency price data from the given URL.

    Args:
        url (str): The URL of the fxpricing widget.

    Returns:
        list: A list of dictionaries, where each dictionary contains
              the extracted data for a currency pair. Returns an empty
              list if fetching or parsing fails.
    """
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()  # Raise an exception for HTTP errors (4xx or 5xx)
    except requests.exceptions.RequestException as e:
        # Instead of printing, we could log this or handle it differently
        # For now, this informs the user if running directly and an issue occurs
        print(f"Error fetching URL: {e}") 
        return []

    soup = BeautifulSoup(response.content, 'html.parser')
    ticker_blocks = soup.find_all('div', class_='ticker-block')

    results = []
    rank = 1
    for block in ticker_blocks:
        name = 'N/A' 
        try:
            name_tag = block.find('strong')
            name = name_tag.text.strip() if name_tag else 'N/A'

            ticker_bottom = block.find('div', class_='ticker-bottom')
            if not ticker_bottom:
                print(f"Warning: Could not find ticker-bottom for item (Rank {rank}, Name: {name}). Skipping.")
                rank +=1
                continue

            bottom_spans = ticker_bottom.find_all('span')
            if len(bottom_spans) < 3:
                print(f"Warning: Not enough data spans in ticker-bottom for {name} (Rank {rank}). Skipping.")
                rank += 1
                continue

            ask_price = bottom_spans[0].text.strip()
            change_percent = bottom_spans[2].text.strip()

            logo_img_tag = block.find('div', class_='circleFlagMain')
            logo_url = 'N/A'
            if logo_img_tag:
                first_img = logo_img_tag.find('img')
                if first_img and first_img.has_attr('src'):
                    logo_url = first_img['src']

            results.append({
                "Rank": rank,
                "Name": name,
                "Slug": name,
                "Price_USD": f"${ask_price}",
                "Daily_Positive_Negative": change_percent,
                "Logo": logo_url
            })
            rank += 1
        except Exception as e:
            print(f"Error parsing a ticker block (Rank {rank}, Name: {name}): {e}")
            rank += 1
            continue
            
    return results

if __name__ == '__main__':
    fx_url = "https://fxpricing.com/fx-widget/ticker-tape-widget.php?id=1,2,3,5,14,20,1972,1984&border=show&speed=50&click_target=blank&theme=light&tm-cr=FFFFFF&hr-cr=00000013&by-cr=28A745&sl-cr=DC3545&flags=circle&d_mode=compact-name&column=ask,bid,spread,chg_per&lang=en&font=Arial,%20sans-serif"
    output_filename = "qoute_price.txt" # Corrected filename based on your request
    
    currency_data = fetch_currency_prices(fx_url)
    
    try:
        with open(output_filename, 'w', encoding='utf-8') as f:
            if not currency_data:
                f.write("No data retrieved.\n")
                print(f"No data retrieved. Results (or this message) saved to {output_filename}")
            else:
                for item in currency_data:
                    f.write(f"Rank: {item['Rank']}\n")
                    f.write(f"Name: {item['Name']}\n")
                    f.write(f"Slug: {item['Slug']}\n")
                    f.write(f"Price_USD: {item['Price_USD']}\n")
                    f.write(f"Daily_Positive_Negative: {item['Daily_Positive_Negative']}\n")
                    f.write(f"Logo: {item['Logo']}\n")
                    f.write("-" * 20 + "\n") # Separator
                print(f"Data successfully saved to {output_filename}")
    except IOError:
        print(f"Error: Could not write to file {output_filename}")
