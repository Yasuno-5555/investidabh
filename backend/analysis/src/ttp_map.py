from typing import List, Dict

class TTPMapper:
    """
    Simple rule-based mapper for MITRE ATT&CK TTPs.
    """
    def __init__(self):
        # Sample subset of Enterprise ATT&CK
        self.rules = {
            "phishing": "T1566",
            "spearphishing": "T1566.002",
            "sql injection": "T1190",
            "sqli": "T1190",
            "xss": "T1190",
            "brute force": "T1110",
            "credential stuffing": "T1110.004",
            "malware": "T1588",
            "ransomware": "T1486",
            "scanning": "T1595",
            "port scan": "T1595.001",
            "command and control": "T1071",
            "c2": "T1071",
            "exfiltration": "T1041",
            "ddos": "T1498"
        }

    def map_text(self, text: str) -> List[str]:
        """
        Scan text for keywords and return list of TTP IDs.
        """
        found_ttps = set()
        text_lower = text.lower()
        for keyword, ttp_id in self.rules.items():
            if keyword in text_lower:
                found_ttps.add(ttp_id)
        return list(found_ttps)
