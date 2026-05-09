from bs4 import BeautifulSoup

from scrapers.characters import extract_actors_data_from_page


def test_extracts_actor_data_from_current_mal_character_table() -> None:
    html = """
    <table border="0" cellpadding="0" cellspacing="0" width="100%">
      <tr>
        <td class="ac borderClass" valign="top" width="27">
          <div class="picSurround">
            <a href="https://myanimelist.net/character/184947/Frieren">
              <img alt="Frieren" data-src="https://example.com/frieren.jpg" />
            </a>
          </div>
        </td>
        <td class="borderClass" valign="top">
          <h3 class="h3_characters_voice_actors">
            <a href="https://myanimelist.net/character/184947/Frieren">Frieren</a>
          </h3>
          <div class="spaceit_pad"><small>Main</small></div>
        </td>
        <td align="right" class="borderClass" valign="top">
          <table border="0" cellpadding="0" cellspacing="0">
            <tr>
              <td class="va-t ar pl4 pr4">
                <a href="https://myanimelist.net/people/17215/Atsumi_Tanezaki">
                  Tanezaki, Atsumi
                </a><br />
                <small>Japanese</small>
              </td>
              <td valign="top">
                <div class="picSurround">
                  <a href="https://myanimelist.net/people/17215/Atsumi_Tanezaki">
                    <img
                      alt="Tanezaki, Atsumi"
                      data-src="https://example.com/atsumi.jpg"
                    />
                  </a>
                </div>
              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>
    """

    result = list(extract_actors_data_from_page(BeautifulSoup(html, 'html.parser')))

    if result != [
        {
            'character_name': 'Frieren',
            'character_photo': 'https://example.com/frieren.jpg',
            'actor_name': 'Tanezaki, Atsumi',
            'actor_photo': 'https://example.com/atsumi.jpg',
        },
    ]:
        raise AssertionError(result)
