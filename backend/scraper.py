"""
Web scraper for conference deadline information.
"""
import csv
import re
from datetime import date, datetime
from typing import List, Optional, Dict
from urllib.parse import urljoin

try:
    import requests
    from bs4 import BeautifulSoup
    HAS_DEPS = True
except ImportError:
    HAS_DEPS = False

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

from models import Deadline, parse_date


class ConferenceScraper:
    """Scrape conference deadline information from websites."""

    GITHUB_RAW_URL = "https://raw.githubusercontent.com/se-deadlines/se-deadlines.github.io/main/_data"

    def __init__(self, proxy: Optional[Dict[str, str]] = None, verify_ssl: bool = True):
        """Initialize the scraper.
        
        Args:
            proxy: Optional dictionary with proxy settings, e.g.:
                   {'http': 'http://proxy:port', 'https': 'https://proxy:port'}
            verify_ssl: Whether to verify SSL certificates (set to False for corporate proxies)
        """
        self.session = None
        self.types_ref = {}  # Local reference from types.yml
        self.verify_ssl = verify_ssl
        if HAS_DEPS:
            self.session = requests.Session()
            self.session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            # Configure proxy if provided
            if proxy:
                self.session.proxies.update(proxy)
                print(f"Proxy configured: {proxy}")
                if not verify_ssl:
                    print("SSL verification disabled for corporate proxy")

    def download_yml_files(self) -> Dict[str, List[dict]]:
        """
        Download conferences.yml and types.yml from GitHub.
        
        Returns:
            Dictionary with 'conferences' and 'types' data
        """
        data = {'conferences': [], 'types': []}
        
        if not HAS_DEPS:
            print("Warning: requests not installed. Cannot download files.")
            return data
        
        try:
            # Download types.yml
            types_url = f"{self.GITHUB_RAW_URL}/types.yml"
            response = self.session.get(types_url, timeout=30, verify=self.verify_ssl)
            response.raise_for_status()
            data['types'] = yaml.safe_load(response.text)
            print(f"Downloaded types.yml: {len(data['types'])} type definitions")
        except Exception as e:
            print(f"Error downloading types.yml: {e}")
        
        try:
            # Download conferences.yml
            conf_url = f"{self.GITHUB_RAW_URL}/conferences.yml"
            response = self.session.get(conf_url, timeout=30, verify=self.verify_ssl)
            response.raise_for_status()
            data['conferences'] = yaml.safe_load(response.text)
            print(f"Downloaded conferences.yml: {len(data['conferences'])} conferences")
        except Exception as e:
            print(f"Error downloading conferences.yml: {e}")
        
        return data

    def load_yml_files(self, types_path: str = "types.yml", 
                       conferences_path: str = "conferences.yml") -> Dict[str, List[dict]]:
        """
        Load conferences.yml and types.yml from local files.
        Use this when GitHub is blocked by corporate firewall.
        
        Args:
            types_path: Path to types.yml file
            conferences_path: Path to conferences.yml file
            
        Returns:
            Dictionary with 'conferences' and 'types' data
        """
        data = {'conferences': [], 'types': []}
        
        try:
            with open(types_path, 'r', encoding='utf-8') as f:
                data['types'] = yaml.safe_load(f)
            print(f"Loaded types.yml: {len(data['types'])} type definitions")
        except Exception as e:
            print(f"Error loading types.yml: {e}")
        
        try:
            with open(conferences_path, 'r', encoding='utf-8') as f:
                data['conferences'] = yaml.safe_load(f)
            print(f"Loaded conferences.yml: {len(data['conferences'])} conferences")
        except Exception as e:
            print(f"Error loading conferences.yml: {e}")
        
        return data

    def build_types_reference(self, types_data: List[dict]) -> Dict[str, dict]:
        """
        Build a local reference dictionary from types.yml data.
        
        Args:
            types_data: List from types.yml
            
        Returns:
            Dictionary mapping tag to type info
        """
        ref = {}
        for item in types_data:
            tag = item.get('tag')
            if tag:
                ref[tag] = {
                    'name': item.get('name', ''),
                    'type': item.get('type', 'others')
                }
        return ref

    def get_venue_type(self, tags: List[str]) -> str:
        """
        Determine if entry is Conference or Workshop based on tags.
        
        Args:
            tags: List of tags from conference entry
            
        Returns:
            'Conference' or 'Workshop' or 'Unknown'
        """
        if 'CO' in tags:
            return 'Conference'
        elif 'WO' in tags:
            return 'Workshop'
        return 'Unknown'

    def get_track_name_from_tags(self, tags: List[str], types_ref: Dict[str, dict]) -> str:
        """
        Infer track name from tags using types reference.
        
        Args:
            tags: List of tags from conference entry
            types_ref: Types reference dictionary
            
        Returns:
            Track name or 'Unknown'
        """
        # Track types to check (in order of priority)
        track_tags = ['RPT', 'IPT', 'SOT', 'NIER', 'JFT', 'EDT', 'TOT', 'SPT', 'RRT', 'EXPT', 'DB', 'RENE']
        
        for tag in tags:
            if tag in track_tags and tag in types_ref:
                return types_ref[tag].get('name', tag)
        
        # Check other types
        other_tags = ['DOS', 'SRC', 'CHT', 'TTBT', 'NFS', 'ART', 'LBT', 'REST', 'FAB', 'POS']
        for tag in tags:
            if tag in other_tags and tag in types_ref:
                return types_ref[tag].get('name', tag)
        
        return 'Unknown'

    def scrape_conference_website(self, url: str) -> dict:
        """
        Scrape a conference website for deadline details.
        
        Args:
            url: URL of the conference website
            
        Returns:
            Dictionary with deadline information
        """
        if not HAS_DEPS:
            return {}
        
        result = {
            'paper_submission': None,
            'abstract_deadline': None,
            'notification': None,
            'extended_abstract': None
        }
        
        try:
            response = self.session.get(url, timeout=30, verify=self.verify_ssl)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Check if this is a conf.researchr.org site
            if 'conf.researchr.org' in url:
                result = self._scrape_researchr_org(soup)
            else:
                # Generic scraping
                result = self._scrape_generic(soup)
            
        except Exception as e:
            print(f"Error scraping {url}: {e}")
        
        return result

    def _scrape_researchr_org(self, soup) -> dict:
        """
        Scrape conf.researchr.org websites for Important Dates.
        
        Args:
            soup: BeautifulSoup object
            
        Returns:
            Dictionary with deadline information
        """
        result = {
            'paper_submission': None,
            'abstract_deadline': None,
            'notification': None,
            'extended_abstract': None
        }
        
        # 1. Target researchr.org sidebar table directly
        sidebar_table = soup.find('table', class_=lambda c: c and 'important-dates-in-sidebar' in c)
        
        if sidebar_table:
            for tr in sidebar_table.find_all('tr'):
                td = tr.find('td')
                if not td:
                    continue
                    
                # stripped_strings separates content around <br> tags into a list:
                # e.g., ["Fri 25 Sep 2026", "Author response period (3 days)"]
                details = list(td.stripped_strings)
                if len(details) >= 2:
                    date_text = details[0]
                    label = details[1].lower()
                    
                    if 'abstract' in label:
                        result['abstract_deadline'] = self._parse_date(date_text)
                    elif 'submission' in label:
                        result['paper_submission'] = self._parse_date(date_text)
                    elif 'notification' in label or 'acceptance' in label:
                        result['notification'] = self._parse_date(date_text)

        # Return early if sidebar extraction succeeded
        if any(result.values()):
            return result

        # 2. Fallback: Check general multi-column tables (2+ cells per row)
        tables = soup.find_all('table')
        for table in tables:
            for row in table.find_all('tr'):
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 2:
                    # Handles tables where date and label are in separate cells
                    text_first = cells[0].get_text().strip()
                    text_second = cells[1].get_text().strip()
                    
                    # Determine which cell contains the label vs the date
                    label = text_first.lower() if not any(char.isdigit() for char in text_first) else text_second.lower()
                    date_text = text_second if label == text_first.lower() else text_first

                    if 'submission' in label and not result['paper_submission']:
                        result['paper_submission'] = self._parse_date(date_text)
                    elif 'abstract' in label and not result['abstract_deadline']:
                        result['abstract_deadline'] = self._parse_date(date_text)
                    elif ('notification' in label or 'acceptance' in label) and not result['notification']:
                        result['notification'] = self._parse_date(date_text)

        # 3. Fallback: Section-based Regex parsing for unstructured HTML
        if not any(result.values()):
            important_dates_section = None
            for heading in soup.find_all(['h2', 'h3', 'h4']):
                if 'important' in heading.get_text().lower() and 'date' in heading.get_text().lower():
                    important_dates_section = heading.parent
                    break
            
            text_content = important_dates_section.get_text() if important_dates_section else soup.get_text()
            
            patterns = {
                'paper_submission': [
                    r'(?:Submission\s*deadline|Submission)[:\s]*([A-Za-z0-9\s,]+(?:202[5-9]))',
                ],
                'abstract_deadline': [
                    r'(?:\(Mandatory\)\s*Abstract|Abstract\s*deadline|Abstract)[:\s]*([A-Za-z0-9\s,]+(?:202[5-9]))',
                ],
                'notification': [
                    r'(?:Acceptance\s*notification|Notification\s*of\s*Acceptance|Notification)[:\s]*([A-Za-z0-9\s,]+(?:202[5-9]))',
                ]
            }
            
            for key, p_list in patterns.items():
                for pattern in p_list:
                    match = re.search(pattern, text_content, re.IGNORECASE)
                    if match:
                        result[key] = self._parse_date(match.group(1))
                        break

        return result
    
    def _scrape_generic(self, soup) -> dict:
        """
        Generic scraping for non-researchr.org websites.
        
        Args:
            soup: BeautifulSoup object
            
        Returns:
            Dictionary with deadline information
        """
        result = {
            'paper_submission': None,
            'abstract_deadline': None,
            'notification': None,
            'extended_abstract': None
        }
        
        text_content = soup.get_text()
        
        # Look for submission deadline patterns
        submission_patterns = [
            r'(?:paper\s*)?submission\s*deadline[:\s]*([A-Za-z0-9\s,]+)',
            r'submit\s*by[:\s]*([A-Za-z0-9\s,]+)',
            r'deadline[:\s]*([A-Za-z0-9\s,]+)',
        ]
        
        for pattern in submission_patterns:
            match = re.search(pattern, text_content, re.IGNORECASE)
            if match:
                result['paper_submission'] = self._parse_date(match.group(1))
                break
        
        # Look for abstract deadline
        abstract_patterns = [
            r'abstract\s*deadline[:\s]*([A-Za-z0-9\s,]+)',
            r'abstract\s*submission[:\s]*([A-Za-z0-9\s,]+)',
        ]
        
        for pattern in abstract_patterns:
            match = re.search(pattern, text_content, re.IGNORECASE)
            if match:
                result['abstract_deadline'] = self._parse_date(match.group(1))
                break
        
        # Look for notification date
        notification_patterns = [
            r'notification\s*date[:\s]*([A-Za-z0-9\s,]+)',
            r'acceptance\s*notification[:\s]*([A-Za-z0-9\s,]+)',
            r'decision\s*date[:\s]*([A-Za-z0-9\s,]+)',
        ]
        
        for pattern in notification_patterns:
            match = re.search(pattern, text_content, re.IGNORECASE)
            if match:
                result['notification'] = self._parse_date(match.group(1))
                break
        
        return result

    def _parse_date(self, date_str: Optional[str]) -> Optional[date]:
        """Parse a date string in various formats."""
        if not date_str:
            return None
        
        date_str = date_str.strip()
        
        formats = [
            "%Y-%m-%d",
            "%B %d, %Y",
            "%b %d, %Y",
            "%d %B %Y",
            "%d %b %Y",
            "%Y/%m/%d",
            "%a %d %b %Y"
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue
        
        return None

    def process_conferences(self, yml_data: Dict[str, List[dict]], 
                           preferred_list_path: Optional[str] = None,
                           scrape_websites: bool = True) -> tuple:
        """
        Process conferences from YAML data and create deadline entries.
        
        Args:
            yml_data: Dictionary with 'conferences' and 'types' lists
            preferred_list_path: Path to preferred conferences CSV
            scrape_websites: Whether to scrape conference websites
            
        Returns:
            Tuple of (deadlines list, missing conferences list, messages list)
        """
        deadlines = []
        missing = []
        messages = []
        
        conferences = yml_data.get('conferences', [])
        types_data = yml_data.get('types', [])
        self.types_ref = self.build_types_reference(types_data)
        
        # Load preferred conferences list (store by conference name and track tag)
        # Format: {conference_name: set of track_tags to match, or None for all tracks}
        preferred = {}  # key: conference_name, value: set of track_tags
        if preferred_list_path:
            try:
                with open(preferred_list_path, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        conf_name = row['conference_name']
                        track_tag = row.get('track_name', '').strip()
                        
                        if conf_name not in preferred:
                            preferred[conf_name] = set()
                        
                        # If track_tag is empty or not provided, this means "match all tracks for this conference"
                        # We use None as a special marker to indicate "match all"
                        if track_tag:
                            preferred[conf_name].add(track_tag)
                        else:
                            preferred[conf_name].add(None)  # None means match all tracks
            except Exception as e:
                messages.append(f"Warning: Could not load preferred list: {e}")
        
        # Track which preferred conferences we found
        found_preferred = set()
        
        for conf in conferences:
            name = conf.get('name', '')
            tags = conf.get('tags', [])
            link = conf.get('link', '')
            
            # Determine venue type
            venue_type = self.get_venue_type(tags)
            
            # Get track name from tags
            track_name = self.get_track_name_from_tags(tags, self.types_ref)
            
            # Get track tag (first track/others tag found)
            track_tag = self._get_track_tag(tags)
            
            # Check if this is in preferred list
            # Match by conference name, and optionally by track tag
            is_preferred = False
            for pref_conf_name, track_tags_for_conf in preferred.items():
                # Check for exact match or prefix match (e.g., "ICSE" matches "ICSE-SEIP")
                # The name must either equal the pref_conf_name, or start with pref_conf_name + '-'
                if name == pref_conf_name or (name.startswith(pref_conf_name + '-') and len(name) > len(pref_conf_name)):
                    # If track_tags_for_conf contains None, match all tracks for this conference
                    if None in track_tags_for_conf:
                        is_preferred = True
                        break
                    elif track_tag in track_tags_for_conf:
                        is_preferred = True
                        break
            
            # Skip if preferred list exists and this isn't in it
            if preferred and not is_preferred:
                continue
            
            if is_preferred:
                found_preferred.add((name, track_tag))
            
            # Get deadlines from YAML
            deadline_list = conf.get('deadline', [])
            if not deadline_list:
                continue
            
            # Handle multiple deadlines
            if not isinstance(deadline_list, list):
                deadline_list = [deadline_list]
            
            for deadline_str in deadline_list:
                # Parse deadline from YAML
                deadline_date = parse_date(deadline_str.split()[0] if ' ' in deadline_str else deadline_str)
                
                if not deadline_date:
                    continue
                
                # Check for abstract deadline in note field
                abstract_deadline = None
                note = conf.get('note', '')
                abstract_match = re.search(r'abstract deadline on ([^.]+)', note, re.IGNORECASE)
                if abstract_match:
                    abstract_deadline = parse_date(abstract_match.group(1).strip())
                
                # Scrape website for additional details if enabled
                if scrape_websites and link:
                    try:
                        scraped = self.scrape_conference_website(link)
                        if scraped.get('abstract_deadline'):
                            abstract_deadline = scraped['abstract_deadline']
                        if scraped.get('notification'):
                            intimation_date = scraped['notification']
                        else:
                            intimation_date = deadline_date
                    except Exception as e:
                        messages.append(f"Warning: Could not scrape {link}: {e}")
                        intimation_date = deadline_date
                else:
                    intimation_date = deadline_date
                
                # Get base conference name for grouping
                base_conf_name = self._get_base_conference_name(name)
                
                # Create deadline entry
                deadline = Deadline(
                    conference_name=base_conf_name,
                    track_name=track_name,
                    workshop_name=None if venue_type == 'Conference' else name,
                    paper_submission_date=deadline_date,
                    abstract_deadline=abstract_deadline,
                    intimation_date=intimation_date
                )
                deadlines.append(deadline)
        
        # Check for missing preferred conferences
        for conf_name, track_tags_for_conf in preferred.items():
            for track_tag in track_tags_for_conf:
                # Skip None (match all tracks) - we don't report missing for this case
                if track_tag is None:
                    continue
                if (conf_name, track_tag) not in found_preferred:
                    # Get track name for display
                    track_name = self.types_ref.get(track_tag, {}).get('name', track_tag)
                    missing.append(f"{conf_name} ({track_name})")
        
        return deadlines, missing, messages

    def _get_track_tag(self, tags: List[str]) -> str:
        """
        Get the first track/others tag from the tags list.
        
        Args:
            tags: List of tags from conference entry
            
        Returns:
            Track tag or empty string
        """
        track_tags = ['RPT', 'IPT', 'SOT', 'NIER', 'JFT', 'EDT', 'TOT', 'SPT', 'RRT', 'EXPT', 'DB', 'RENE',
                      'DOS', 'SRC', 'CHT', 'TTBT', 'NFS', 'ART', 'LBT', 'REST', 'FAB', 'POS']
        for tag in tags:
            if tag in track_tags:
                return tag
        return ''

    def _get_base_conference_name(self, name: str) -> str:
        """
        Extract the base conference name from a full name.
        
        For example:
        - "ICSE" -> "ICSE"
        - "ICSE-SEIP" -> "ICSE"
        - "ICSE-NIER" -> "ICSE"
        - "FSE" -> "FSE"
        - "FSE-IP" -> "FSE"
        
        Args:
            name: Full conference/track name
            
        Returns:
            Base conference name
        """
        # Check if name contains a hyphen followed by uppercase letters (track suffix)
        if '-' in name:
            parts = name.split('-', 1)
            # If the part after hyphen is all uppercase or starts with uppercase,
            # it's likely a track suffix
            suffix = parts[1]
            if suffix.isupper() or (len(suffix) > 0 and suffix[0].isupper() and suffix.isalpha()):
                return parts[0]
        return name

    def save_preferred_to_csv(self, deadlines: List[Deadline], output_path: str):
        """
        Save preferred conference deadlines to a separate CSV file.
        
        Args:
            deadlines: List of Deadline objects
            output_path: Path to output CSV file
        """
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            fieldnames = ['conference_name', 'track_name', 'workshop_name',
                         'paper_submission_date', 'abstract_deadline', 'intimation_date']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for d in deadlines:
                writer.writerow({
                    'conference_name': d.conference_name,
                    'track_name': d.track_name,
                    'workshop_name': d.workshop_name or '',
                    'paper_submission_date': d.paper_submission_date.isoformat() if d.paper_submission_date else '',
                    'abstract_deadline': d.abstract_deadline.isoformat() if d.abstract_deadline else '',
                    'intimation_date': d.intimation_date.isoformat() if d.intimation_date else '',
                })

    def save_to_csv(self, deadlines: List[Deadline], output_path: str):
        """
        Save scraped deadlines to CSV file.
        
        Args:
            deadlines: List of Deadline objects
            output_path: Path to output CSV file
        """
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            fieldnames = ['conference_name', 'track_name', 'workshop_name',
                         'paper_submission_date', 'abstract_deadline', 'intimation_date']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for d in deadlines:
                writer.writerow({
                    'conference_name': d.conference_name,
                    'track_name': d.track_name,
                    'workshop_name': d.workshop_name or '',
                    'paper_submission_date': d.paper_submission_date.isoformat() if d.paper_submission_date else '',
                    'abstract_deadline': d.abstract_deadline.isoformat() if d.abstract_deadline else '',
                    'intimation_date': d.intimation_date.isoformat() if d.intimation_date else '',
                })


if __name__ == "__main__":
    # Example usage
    # Configure proxy if needed (e.g., for corporate networks)
    proxy = None  # Set to None to use direct connection
    verify_ssl = True  # Set to False if using corporate proxy with self-signed certs
    
    scraper = ConferenceScraper(proxy=proxy, verify_ssl=verify_ssl)
    
    # Try to download YAML files from GitHub
    yml_data = scraper.download_yml_files()
    
    # If download failed, try loading from local files
    if not yml_data['conferences']:
        print("\nTrying to load from local files...")
        # Try multiple possible locations for the YAML files
        import os
        possible_paths = [
            ("types.yml", "conferences.yml"),  # Same directory
            ("../types.yml", "../conferences.yml"),  # Parent directory (when running from backend/)
            ("../../types.yml", "../../conferences.yml"),  # Two levels up
        ]
        
        for types_path, conf_path in possible_paths:
            if os.path.exists(types_path) and os.path.exists(conf_path):
                yml_data = scraper.load_yml_files(types_path=types_path, conferences_path=conf_path)
                if yml_data['conferences']:
                    break
    
    # Check if we got any data
    if not yml_data['conferences']:
        print("\nWarning: No conference data available.")
        print("Please either:")
        print("  1. Check network connectivity")
        print("  2. Download YAML files manually from GitHub and place in project root")
        print("  3. Use a different network connection")
        exit(1)
    
    # Process conferences with preferred list
    deadlines, missing, messages = scraper.process_conferences(
        yml_data, 
        preferred_list_path="data/preferred_conferences.csv"
    )
    
    # Print messages
    for msg in messages:
        print(msg)
    
    # Print missing conferences
    if missing:
        print("\nMissing preferred conferences:")
        for m in missing:
            print(f"  - {m}")
    
    # Save to main CSV (all deadlines from preferred list)
    scraper.save_to_csv(deadlines, "data/conferences.csv")
    print(f"\nSaved {len(deadlines)} deadlines to data/conferences.csv")
    
    # Save to preferred CSV (same content, separate file)
    scraper.save_preferred_to_csv(deadlines, "data/preferred_conferences_output.csv")
    print(f"Saved {len(deadlines)} deadlines to data/preferred_conferences_output.csv")