import requests
from bs4 import BeautifulSoup

def get_page_content(url):
    """
    Fetches and parses the content of a given URL.
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Raises an HTTPError for bad responses (4xx or 5xx)
        response.encoding = response.apparent_encoding # Or manually set to 'utf-8' if you know the encoding

        soup = BeautifulSoup(response.text, 'html.parser')

        # Find the main content container using its class name
        content_div = soup.find('div', class_='view')

        if content_div:
            # Extract text from the content div
            text = content_div.get_text(separator='\n', strip=True)
            return text
        else:
            return f"Could not find the content container with class='view'.\n\nFull HTML:\n{soup.prettify()}"

    except requests.exceptions.RequestException as e:
        return f"An error occurred: {e}"

if __name__ == '__main__':
    url = "https://www.cq.gov.cn/zwgk/zfxxgkml/szfwj/qtgw/202506/t20250606_14692232.html"
    content = get_page_content(url)
    print(content) 