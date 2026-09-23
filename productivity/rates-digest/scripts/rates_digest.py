#!/usr/bin/env python3
"""Курсы валют USD/RUB с cbr.ru."""
import xml.etree.ElementTree as ET
import urllib.request

CBR_URL = "https://www.cbr.ru/scripts/XML_daily.asp"

def main():
    try:
        with urllib.request.urlopen(CBR_URL, timeout=10) as resp:
            tree = ET.parse(resp)
        root = tree.getroot()
    except Exception as e:
        print(f"❌ Ошибка загрузки курсов: {e}")
        return

    rates = {}
    for valute in root.findall('Valute'):
        code = valute.find('CharCode').text
        value = valute.find('Value').text
        nominal = valute.find('Nominal').text or '1'
        if code in ('USD', 'EUR', 'CNY'):
            val = float(value.replace(',', '.')) / int(nominal)
            rates[code] = val

    print("💰 **Курсы валют (ЦБ РФ):**")
    for code in ('USD', 'EUR', 'CNY'):
        if code in rates:
            print(f"{code}: {rates[code]:.2f} ₽")

if __name__ == '__main__':
    main()