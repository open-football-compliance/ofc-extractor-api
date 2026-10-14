import re
import time
import requests
import unicodedata
import urllib3
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from typing import List, Dict

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class CBFScraperService:
    """
    Service responsible for searching and downloading CBF match-day financial report PDFs.
    Dynamically maps teams across all national divisions.
    """

    COMPETITIONS = {
        "serie-a": "https://www.cbf.com.br/futebol-brasileiro/times/campeonato-brasileiro/serie-a/2026",
        "serie-b": "https://www.cbf.com.br/futebol-brasileiro/times/campeonato-brasileiro/serie-b/2026",
        "serie-c": "https://www.cbf.com.br/futebol-brasileiro/times/campeonato-brasileiro/serie-c/2026",
        "serie-d": "https://www.cbf.com.br/futebol-brasileiro/times/campeonato-brasileiro/serie-d/2026"
    }   

    @staticmethod
    def _normalize_text(text: str) -> str:
        """Remove acentos e converte para minúsculas (ex: 'Náutico' -> 'nautico')"""
        if not text:
            return ""
        text = unicodedata.normalize('NFD', text)
        return ''.join(c for c in text if unicodedata.category(c) != 'Mn').lower()

    @staticmethod
    def fetch_pdf_bytes_by_team(team_name: str) -> List[Dict[str, bytes]]:
        """
        Extracts PDF bytes of match reports for a specific team across all divisions.
        """
        pdfs_data = []
        scraper = CBFScraperService()

        normalized_target = scraper._normalize_text(team_name).strip()
        
        print(f"Searching for team: {team_name}")
        for competition, url in scraper.COMPETITIONS.items():
            teams_data = scraper.find_teams(url)
            
            team_info = next(
                (t for t in teams_data if normalized_target in scraper._normalize_text(t["name"]).strip()), 
                None
            )
            
            if not team_info:
                continue
                
            print(f"Found {team_info['name']} in {competition}. Scanning their match history.")
            pdfs_data.extend(scraper._scrape_team_matches(team_info['url'], normalized_target))
            
            break
            
        return pdfs_data

    def find_teams(self, competition_url: str) -> List[Dict[str, str]]:
        """
        Maps team names and their respective profile links for a given competition.
        """
        teams_data = []
        
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()

                page.route("**/*", lambda route: route.abort() 
                           if route.request.resource_type in ["image", "stylesheet", "font", "media"] 
                           else route.continue_())

                page.goto(competition_url)
                
                page.wait_for_selector('div[class^="styles_clubs_"]')
                soup = BeautifulSoup(page.content(), 'html.parser')
                
                clubs_div = soup.find('div', class_=re.compile(r'^styles_clubs_'))
                if not clubs_div:
                    return []
                
                team_links = clubs_div.find_all('a', class_=re.compile(r'^styles_container_'))
                
                for link in team_links:
                    href = link.get('href')
                    strong_tag = link.find('strong')
                    
                    if strong_tag and href:
                        raw_text = strong_tag.get_text(separator=" ", strip=True)
                        clean_name = re.sub(r'\s*-\s*[A-Z]{2}$', '', raw_text).strip()
                        full_url = f"https://www.cbf.com.br{href}?tab=historico-de-partidas"
                        
                        teams_data.append({"name": clean_name, "url": full_url})
                        
                browser.close()
        except Exception as e:
            print(f"Error finding teams at {competition_url}: {e}")
            
        return teams_data

    def _scrape_team_matches(self, url_historico: str, team_normalized: str) -> List[Dict[str, bytes]]:
        """
        Internal method to scrape all borderôs given a team's specific history URL.
        """
        pdfs_data = []
        
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()

                page.route("**/*", lambda route: route.abort() 
                           if route.request.resource_type in ["image", "stylesheet", "font", "media"] 
                           else route.continue_())
                
                page.goto(url_historico)
                page.wait_for_load_state("networkidle")
                
                soup_historico = BeautifulSoup(page.content(), 'html.parser')
                links_jogos = soup_historico.find_all('a', href=re.compile(r'/campeonato-brasileiro/serie-[a-d]/\d{4}/[^/]*/\d+'))
                
                urls_partidas = set()
                for link in links_jogos:
                    href = link.get('href')
                    if href and href.startswith('/'):
                        parts = href.strip('/').split('/')
                        if len(parts) >= 2:
                            match_slug = parts[-2] 
                            
                            if '-x-' in match_slug:
                                home_team_slug = match_slug.split('-x-')[0]
                                team_slug_format = team_normalized.replace(" ", "-")
                                
                                if team_slug_format in home_team_slug:
                                    urls_partidas.add(f"https://www.cbf.com.br{href}")
                    
                lista_jogos = list(urls_partidas)
                
                for i, url_jogo in enumerate(lista_jogos):
                    url_documentos = f"{url_jogo}?view=documentos"
                    
                    try:
                        response_doc = requests.get(url_documentos, verify=False)
                        soup_jogo = BeautifulSoup(response_doc.content, 'html.parser')
                        link_bordero = soup_jogo.find('a', href=re.compile(r'b\.pdf$'))
                        
                        if link_bordero:
                            url_pdf = link_bordero.get('href')
                            
                            response = requests.get(url_pdf, verify=False)
                            response.raise_for_status()
                            
                            pdfs_data.append({"url": url_pdf, "bytes": response.content})
                            
                    except Exception as e:
                        print(f"Error processing {url_documentos}: {e}")
                    
                browser.close()
                print(f"Completed scraping for team. Total PDFs found: {len(pdfs_data)}")
        except Exception as e:
            print(f"Error scraping match history: {e}")
            
        return pdfs_data