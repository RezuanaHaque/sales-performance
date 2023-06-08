import json
import time
import warnings
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from google.oauth2 import service_account

# drive link: https://drive.google.com/drive/u/2/folders/1kSDkodTVlAQ5B68sHxGFDXcP_-SzkNvZ# drive link: https://drive.google.com/drive/u/2/folders/1kSDkodTVlAQ5B68sHxGFDXcP_-SzkNvZ

creds_file_path = 'E:/Web_scrape/strange-radius-389119-251b13aa5a58.json'
scopes = ['https://www.googleapis.com/auth/drive', 'https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive.file']
creds = service_account.Credentials.from_service_account_file(creds_file_path, scopes=scopes)
drive_service = build('drive', 'v3', credentials=creds)
sheets_service = build('sheets', 'v4', credentials=creds)
# print(drive_service, sheets_service)

file_metadata = {
    'name': 'order_details',
    'parents': ['1kSDkodTVlAQ5B68sHxGFDXcP_-SzkNvZ'],
    'mimeType': 'application/vnd.google-apps.spreadsheet'
}
spreadsheet = drive_service.files().create(body=file_metadata, fields='id').execute()
main_sheet_id = spreadsheet['id']

sheet_range = 'A:H'
column_names = ['Order ID', 'Dish Name', 'Restaurant', 'Dish Price', 'Date', 'Discount', 'Final Price', 'Order Volumn']
values = [column_names]
# print(values)



sheet_id = '1AuTymXzSH5cUIQoaEN9Ugf7gChuIKMOCAX1MAvSIh_0' # replace with your sheet ID
range_name = 'Sheet1!A:B' # replace with the range of the sheet where the phone numbers and passwords are stored
result = sheets_service.spreadsheets().values().get(spreadsheetId=sheet_id, range=range_name).execute()
# print(result)
values = result.get('values', [])
# print(values)
phones = [row[0] for row in values[1:]]
passwords = [row[1] for row in values[1:]]

# Loop through each restaurant and get their order details
for phone, password in zip(phones, passwords):
    options = webdriver.ChromeOptions()
    options.add_argument("--log-level=3")
    # options.add_argument("--headless")
    options.add_argument("--window-size=1920x1080")
    driver = webdriver.Chrome(options=options)
    # driver.get(url)
    driver.get('https://merchant-ca.hungrypanda.co/login')
    username_input = driver.find_element(By.XPATH, '//input[@id="phone"]')
    password_input = driver.find_element(By.XPATH, '//input[@id="password"]')
    username_input.send_keys(phone)
    password_input.send_keys(password)
    password_input.send_keys(Keys.RETURN)


    time.sleep(3)


    local_storage = driver.execute_script("return window.localStorage;")
    local_storage_data = json.loads(local_storage['LOCALSTORE_USERINFOTABLE'])
    token = local_storage_data['token']



    orders_link = driver.find_element(By.XPATH, '//div[@class="menus-item-name" and text()="Orders"]')
    orders_link.click()
    wait = WebDriverWait(driver, 20)
    html = driver.page_source
    soup = BeautifulSoup(html, "html.parser")
    span_tag = soup.span
    restaurant_name = span_tag.text
    url = "https://ca-gateway.hungrypanda.co/api/merchant/order/list"
    headers = {"token": token}
    payload = {
    "pageNo": 1,
    "pageSize": 10,
}
    orders_data = []
    response = requests.post(url, json=payload, headers=headers)
    data = json.loads(response.content.decode())
    orders_data.extend(data['data']['orders']['list'])
    time.sleep(5)

    while True:
        next_button = driver.find_element(By.XPATH,  '//li[@title="Next Page"]')
        if 'ant-pagination-disabled' in next_button.get_attribute('class') or next_button.get_attribute('aria-disabled') == 'true':
            driver.quit()
            break
        next_button.click()
        # time.sleep(2)
        page = payload["pageNo"]
        payload["pageNo"] = page + 1
        response = requests.post(url, json=payload, headers=headers)
        # time.sleep(3)
        data = json.loads(response.content.decode())
        # time.sleep(3)
        orders_data.extend(data['data']['orders']['list'])
        # time.sleep(3)

    order_ids = [order["orderSn"] for order in orders_data]

    # print("hhhhhhhhhhhhhhhhhhhh", order_ids)


    restaurant_sheet_body = {'requests': [{'addSheet': {'properties': {'title': restaurant_name}} } ]}
    print("hhhhhhhhhhhhhhhhhhhh", restaurant_sheet_body)
    restaurant_sheet = sheets_service.spreadsheets().batchUpdate(spreadsheetId=main_sheet_id, body=restaurant_sheet_body).execute()
    restaurant_sheet_id = restaurant_sheet['replies'][0]['addSheet']['properties']['sheetId']
    sheet_range = f"{restaurant_name}!A:H"
    values = [['Order ID', 'Dish Name', 'Restaurant', 'Dish Price', 'Date', 'Discount', 'Final Price', 'Order Volumn']] 


    for i, order_id in enumerate(order_ids):
        url = "https://ca-gateway.hungrypanda.co/api/merchant/order/detail"
        headers = {
            "Content-Type": "application/json",
            "token": token
        }
        payload = {
    "orderSn": order_id
}
        response = requests.post(url, headers=headers, json=payload)
        # time.sleep(5)
        data = response.json()["data"]
        print("dddddddddddddddddddd", data)
        if data:
            # extract the order details
            order_id = order_id
            dish_names = [detail["productName"] for detail in data["details"]]
            restaurant_name = span_tag.text
            dish_prices = [detail["productPrice"] for detail in data["details"]]
            date = data["createTime"]
            discounts = data["fullSubRedRespDTO"]["firstDiscount"]
            final_price = data["fixedPrice"]
            order_volumes = [detail["productCount"] for detail in data["details"]]
            # join the dish names, prices, and volumes with a comma separator
            dish_names_str = ", ".join(str(dish_name) for dish_name in dish_names)
            dish_prices_str = ", ".join(str(price) for price in dish_prices)
            order_volumes_str = ", ".join(str(volume) for volume in order_volumes)
            # time.sleep(5)
            values.append([order_id, dish_names_str, restaurant_name, dish_prices_str, date, discounts, final_price, order_volumes_str])
    data_body = {
        'values': values
    }
    # time.sleep(5)
    update_request_body = {
        'valueInputOption': 'RAW',
        'data': [
            {
                'range': sheet_range,
                'majorDimension': 'ROWS',
                'values': values
            }
        ]
    }
    time.sleep(3)
    sheets_service.spreadsheets().values().batchUpdate(spreadsheetId=main_sheet_id, body=update_request_body).execute()

