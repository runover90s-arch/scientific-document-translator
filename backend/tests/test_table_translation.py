import asyncio

from bs4 import BeautifulSoup

from app.services.pipeline import _translate_html_table


class FakeTranslator:
    async def translate(self, text, source_language, target_language, context=""):
        return text.replace("Density", "Khối lượng riêng").replace("Temperature", "Nhiệt độ")


def test_html_table_roundtrip_parse():
    html = '<table><tr><td>Density</td><td>8960</td></tr></table>'
    soup = BeautifulSoup(html, 'html.parser')
    assert soup.find_all('td')[0].get_text() == 'Density'
    assert soup.find_all('td')[1].get_text() == '8960'


def test_table_translation_preserves_nested_scientific_markup():
    source = '<table><tr><th>Density</th><td>kg/m<sup>3</sup></td><td>ρ = 8960</td></tr></table>'
    translated = asyncio.run(_translate_html_table(source, FakeTranslator(), 'en', 'vi', ''))
    soup = BeautifulSoup(translated, 'html.parser')

    assert soup.find('th').get_text() == 'Khối lượng riêng'
    assert soup.find('sup') is not None
    assert soup.find('sup').get_text() == '3'
    assert 'ρ' in soup.get_text()
    assert '8960' in soup.get_text()


def test_table_translation_keeps_caption_and_footnote_around_table():
    source = '<p class="table-caption">Density table</p><table><tr><td>8960</td></tr></table><p class="table-footnote">Temperature note</p>'
    translated = asyncio.run(_translate_html_table(source, FakeTranslator(), 'en', 'vi', ''))
    soup = BeautifulSoup(translated, 'html.parser')

    assert 'Khối lượng riêng table' in soup.get_text(' ')
    assert 'Nhiệt độ note' in soup.get_text(' ')
    assert soup.find('table') is not None
    assert soup.find('td').get_text() == '8960'
