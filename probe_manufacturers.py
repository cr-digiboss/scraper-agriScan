"""
Script de sondage temporaire — à supprimer après usage.
Debug New Holland round 5 : la galerie de cartes "MODÈLES" contient 9
modèles (7616..7641) mais le <table> de specs n'a que 6 colonnes
(7616..7628), même après clic sur "VOIR PLUS DE MODÈLES" (qui ne fait
que révéler des cartes supplémentaires, sans toucher au tableau). On
vérifie ici si les codes des 3 modèles manquants (7630, 7635, 7641)
existent QUAND MÊME ailleurs dans le DOM du tableau (texte caché, lignes
d'en-tête supplémentaires, etc.) avant de conclure que la donnée est
simplement absente du tableau sur le site source.
"""

import json
import logging

from playwright.sync_api import sync_playwright

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("probe")

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

URL = "https://agriculture.newholland.com/fr-be/europe/produits/moissonneuses-batteuses/barres-de-coupe-varifeed-pour-moissonneuses-batteuses"

MISSING_CODES = ["7630", "7635", "7641"]


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(user_agent=UA)
        page.goto(URL, timeout=30000, wait_until="domcontentloaded")
        page.wait_for_timeout(4000)

        try:
            accept = page.locator("#onetrust-accept-btn-handler")
            if accept.is_visible(timeout=3000):
                accept.click(timeout=3000)
                page.wait_for_timeout(1000)
        except Exception:
            pass

        # 1) Les codes manquants apparaissent-ils n'importe où dans le <table> ?
        search_result = page.evaluate(
            """
            (codes) => {
                const table = document.querySelector('table');
                if (!table) return {found: false};
                const fullText = table.innerText;
                const fullHTML = table.innerHTML;
                return {
                    found: true,
                    textLen: fullText.length,
                    presentInText: codes.map(c => ({code: c, inText: fullText.includes(c), inHTML: fullHTML.includes(c)})),
                    nRows: table.querySelectorAll('tr').length,
                };
            }
            """,
            MISSING_CODES,
        )
        log.info(f"Recherche codes manquants dans <table> : {json.dumps(search_result, ensure_ascii=False, indent=2)}")

        # 2) Grille complète (colspan/rowspan-aware) du tableau, pour inspection humaine.
        grid = page.evaluate(
            """
            () => {
                const table = document.querySelector('table');
                if (!table) return null;
                const rows = Array.from(table.querySelectorAll('tr'));
                const grid = [];
                rows.forEach((row, rIdx) => {
                    const cells = Array.from(row.querySelectorAll('td, th'));
                    if (!grid[rIdx]) grid[rIdx] = [];
                    let colIdx = 0;
                    cells.forEach(cell => {
                        while (grid[rIdx][colIdx] !== undefined) colIdx++;
                        const colspan = cell.colSpan || 1;
                        const rowspan = cell.rowSpan || 1;
                        const text = cell.innerText.trim();
                        for (let r = 0; r < rowspan; r++) {
                            if (!grid[rIdx + r]) grid[rIdx + r] = [];
                            for (let c = 0; c < colspan; c++) {
                                grid[rIdx + r][colIdx + c] = text;
                            }
                        }
                        colIdx += colspan;
                    });
                });
                return grid.slice(0, 3);
            }
            """
        )
        log.info(f"\n3 premières lignes de la grille du tableau : {json.dumps(grid, ensure_ascii=False, indent=2)}")

        # 3) Est-ce qu'il y a un élément parent/sibling avec data-* liant cartes <-> colonnes ?
        card_attrs = page.evaluate(
            """
            () => {
                const cards = Array.from(document.querySelectorAll('.model-listing__card'));
                return cards.map(c => ({
                    text60: c.innerText.trim().slice(0, 30),
                    attrs: Array.from(c.attributes).map(a => `${a.name}=${a.value}`),
                }));
            }
            """
        )
        log.info(f"\nAttributs des cartes : {json.dumps(card_attrs, ensure_ascii=False, indent=2)}")

        browser.close()


if __name__ == "__main__":
    main()
