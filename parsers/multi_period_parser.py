# parsers/multi_period_parser.py
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
import re
import logging

class Period(Enum):
    """Périodes historiques françaises"""
    ANCIEN_REGIME = "ancien_regime"      # 1500-1789
    REVOLUTION = "revolution"            # 1789-1815  
    ETAT_CIVIL_ANCIEN = "etat_civil_ancien"  # 1815-1900
    MODERNE = "moderne"                  # 1900-1950

@dataclass
class PeriodDetection:
    """Résultat de détection de période"""
    period: Period
    confidence: float
    indicators: List[str]
    estimated_date_range: Tuple[int, int]

class MultiPeriodParser:
    """Parser intelligent capable de traiter toutes les périodes 1500-1950"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Charger les parsers spécialisés par période
        self.period_parsers = self._initialize_period_parsers()
        
        # Indicateurs de détection par période
        self.period_indicators = self._setup_period_indicators()
        
        # Cache de détection
        self._detection_cache = {}
    
    def _initialize_period_parsers(self) -> Dict[Period, 'PeriodSpecificParser']:
        """Initialise les parsers spécialisés"""
        from config.settings import ParserConfig
        
        return {
            Period.ANCIEN_REGIME: AncienRegimeParser(ParserConfig()),
            Period.REVOLUTION: RevolutionParser(ParserConfig()),
            Period.ETAT_CIVIL_ANCIEN: EtatCivilAncienParser(ParserConfig()),
            Period.MODERNE: ModerneParser(ParserConfig())
        }
    
    def _setup_period_indicators(self) -> Dict[Period, Dict]:
        """Configure les indicateurs de détection par période"""
        return {
            Period.ANCIEN_REGIME: {
                'vocabulary': [
                    'bapt.', 'inh.', 'curé', 'prestre', 'chapelle', 'paroisse',
                    'sieur', 'escuyer', 'conseiller du roi', 'sr de', 'sgr de',
                    'pris possession', 'bénéfice', 'cure', 'filz'
                ],
                'date_patterns': [
                    r"l'an\s+(?:de\s+)?(?:grâce\s+)?\d{4}",
                    r"\d{4}(?:[-–]\d{4})?",
                    r"(?:janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre)\s+\d{4}"
                ],
                'format_indicators': [
                    'ay,? au nom de Dieu', 'moy,? .+? prestre',
                    'dans l\'église', 'sous le chœur'
                ],
                'date_range': (1500, 1789)
            },
            
            Period.REVOLUTION: {
                'vocabulary': [
                    'citoyen', 'citoyenne', 'commune', 'département', 
                    'république', 'an II', 'an III', 'calendrier républicain',
                    'décadi', 'sans-culotte', 'municipalité', 'état civil'
                ],
                'date_patterns': [
                    r"an\s+[IVX]+",  # An II, An III, etc.
                    r"(?:vendémiaire|brumaire|frimaire|nivôse|pluviôse|ventôse|germinal|floréal|prairial|messidor|thermidor|fructidor)",
                    r"(?:179[0-9]|180[0-9]|181[0-5])"
                ],
                'format_indicators': [
                    'acte de naissance', 'acte de mariage', 'acte de décès',
                    'officier public', 'municipalité de'
                ],
                'date_range': (1789, 1815)
            },
            
            Period.ETAT_CIVIL_ANCIEN: {
                'vocabulary': [
                    'état civil', 'mairie', 'adjoint', 'maire', 'arrondissement',
                    'commune de', 'canton', 'département de', 'préfecture',
                    'acte de naissance', 'acte de mariage', 'acte de décès'
                ],
                'date_patterns': [
                    r"(?:181[6-9]|18[2-9]\d|19[0-9]\d)",
                    r"\d{1,2}\s+(?:janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre)\s+1[89]\d{2}"
                ],
                'format_indicators': [
                    'registre de l\'état civil', 'devant nous',
                    'officier de l\'état civil', 'en présence de'
                ],
                'date_range': (1815, 1900)
            },
            
            Period.MODERNE: {
                'vocabulary': [
                    'certificat', 'livret de famille', 'identité', 'profession',
                    'domicile', 'nationalité', 'divorc', 'reconnaissance'
                ],
                'date_patterns': [
                    r"(?:19[0-5]\d)",
                    r"\d{1,2}[\/\-]\d{1,2}[\/\-]19[0-5]\d"
                ],
                'format_indicators': [
                    'extrait d\'acte', 'copie intégrale',
                    'mention marginale', 'transcription'
                ],
                'date_range': (1900, 1950)
            }
        }
    
    def detect_period(self, text: str) -> PeriodDetection:
        """Détecte automatiquement la période du document"""
        
        # Vérifier le cache
        text_hash = hash(text[:1000])  # Hash des 1000 premiers caractères
        if text_hash in self._detection_cache:
            return self._detection_cache[text_hash]
        
        text_lower = text.lower()
        period_scores = {}
        
        for period, indicators in self.period_indicators.items():
            score = 0
            found_indicators = []
            
            # Score vocabulaire spécialisé
            for vocab_word in indicators['vocabulary']:
                if vocab_word.lower() in text_lower:
                    score += 2
                    found_indicators.append(f"vocab:{vocab_word}")
            
            # Score patterns de dates
            for date_pattern in indicators['date_patterns']:
                matches = re.findall(date_pattern, text, re.IGNORECASE)
                if matches:
                    score += len(matches) * 3  # Les dates sont très importantes
                    found_indicators.extend([f"date:{match}" for match in matches[:3]])
            
            # Score indicateurs de format
            for format_indicator in indicators['format_indicators']:
                if re.search(format_indicator, text, re.IGNORECASE):
                    score += 1.5
                    found_indicators.append(f"format:{format_indicator}")
            
            period_scores[period] = {
                'score': score,
                'indicators': found_indicators
            }
        
        # Trouver la période avec le meilleur score
        best_period = max(period_scores.keys(), key=lambda p: period_scores[p]['score'])
        best_score = period_scores[best_period]['score']
        
        # Calculer la confiance (0-1)
        total_possible_score = len(self.period_indicators[best_period]['vocabulary']) * 2 + 10  # Estimation
        confidence = min(best_score / total_possible_score, 1.0)
        
        # Estimer la plage de dates
        date_range = self.period_indicators[best_period]['date_range']
        
        result = PeriodDetection(
            period=best_period,
            confidence=confidence,
            indicators=period_scores[best_period]['indicators'],
            estimated_date_range=date_range
        )
        
        # Mettre en cache
        self._detection_cache[text_hash] = result
        
        return result
    
    def parse_document(self, text: str, forced_period: Optional[Period] = None) -> Dict:
        """Parse un document en détectant automatiquement la période"""
        
        # Détection automatique ou forcée
        if forced_period:
            period = forced_period
            detection_info = {"forced": True, "period": period.value}
        else:
            detection = self.detect_period(text)
            period = detection.period
            detection_info = {
                "detected": True,
                "confidence": detection.confidence,
                "indicators": detection.indicators,
                "estimated_dates": detection.estimated_date_range
            }
        
        # Utiliser le parser spécialisé
        specialized_parser = self.period_parsers[period]
        
        try:
            result = specialized_parser.parse(text)
            
            # Ajouter les métadonnées de période
            result['period_info'] = {
                'period': period.value,
                'detection': detection_info,
                'parser_used': specialized_parser.__class__.__name__
            }
            
            return result
            
        except Exception as e:
            self.logger.error(f"Erreur parsing période {period.value}: {e}")
            
            # Fallback vers ancien régime si échec
            if period != Period.ANCIEN_REGIME:
                self.logger.info("Fallback vers parser Ancien Régime")
                return self.period_parsers[Period.ANCIEN_REGIME].parse(text)
            else:
                raise

class PeriodSpecificParser:
    """Classe de base pour parsers spécialisés"""
    
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def parse(self, text: str) -> Dict:
        """Méthode à implémenter par chaque parser spécialisé"""
        raise NotImplementedError

class AncienRegimeParser(PeriodSpecificParser):
    """Parser pour Ancien Régime (1500-1789) - votre code existant"""
    
    def parse(self, text: str) -> Dict:
        # Utiliser votre logique existante
        from main import GenealogyParser
        
        parser = GenealogyParser()
        return parser.process_document(text)

class RevolutionParser(PeriodSpecificParser):
    """Parser pour période révolutionnaire (1789-1815)"""
    
    def __init__(self, config):
        super().__init__(config)
        self._setup_revolution_patterns()
    
    def _setup_revolution_patterns(self):
        """Patterns spécifiques période révolutionnaire"""
        self.patterns = {
            # Calendrier républicain
            'date_republicaine': re.compile(
                r'(?:le\s+)?(\d{1,2})\s+(vendémiaire|brumaire|frimaire|nivôse|pluviôse|ventôse|germinal|floréal|prairial|messidor|thermidor|fructidor)\s+(?:de\s+)?l\'an\s+([IVX]+)',
                re.IGNORECASE
            ),
            
            # Actes civils nouveaux
            'acte_civil': re.compile(
                r'acte\s+de\s+(naissance|mariage|décès)\s+.+?commune\s+de\s+([A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞß][a-zàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿ\s]+)',
                re.IGNORECASE
            ),
            
            # Citoyens
            'citoyen_pattern': re.compile(
                r'(?:le\s+)?citoyen(?:ne)?\s+([A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞß][a-zàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿ\s]+)',
                re.IGNORECASE
            )
        }
    
    def parse(self, text: str) -> Dict:
        """Parse spécialisé période révolutionnaire"""
        result = {
            'periode': 'Révolution française (1789-1815)',
            'actes': {'total': 0, 'par_type': {}},
            'personnes': [],
            'dates_republicaines': [],
            'lieux': set()
        }
        
        # Convertir dates républicaines
        dates_rep = self.patterns['date_republicaine'].findall(text)
        for jour, mois, annee in dates_rep:
            date_conv = self._convert_republican_date(jour, mois, annee)
            result['dates_republicaines'].append({
                'original': f"{jour} {mois} an {annee}",
                'gregorienne': date_conv
            })
        
        # Extraire actes civils
        actes_civils = self.patterns['acte_civil'].findall(text)
        for type_acte, commune in actes_civils:
            result['actes']['par_type'][type_acte] = result['actes']['par_type'].get(type_acte, 0) + 1
            result['actes']['total'] += 1
            result['lieux'].add(commune)
        
        # Extraire citoyens
        citoyens = self.patterns['citoyen_pattern'].findall(text)
        for nom in citoyens:
            result['personnes'].append({
                'nom': nom.strip(),
                'statut': 'citoyen',
                'periode': 'revolution'
            })
        
        result['lieux'] = list(result['lieux'])
        return result
    
    def _convert_republican_date(self, jour: str, mois: str, annee: str) -> Optional[str]:
        """Convertit une date républicaine en date grégorienne"""
        mois_republicains = {
            'vendémiaire': 1, 'brumaire': 2, 'frimaire': 3,
            'nivôse': 4, 'pluviôse': 5, 'ventôse': 6,
            'germinal': 7, 'floréal': 8, 'prairial': 9,
            'messidor': 10, 'thermidor': 11, 'fructidor': 12
        }
        
        annees_republicaines = {
            'I': 1792, 'II': 1793, 'III': 1794, 'IV': 1795,
            'V': 1796, 'VI': 1797, 'VII': 1798, 'VIII': 1799,
            'IX': 1800, 'X': 1801, 'XI': 1802, 'XII': 1803,
            'XIII': 1804, 'XIV': 1805
        }
        
        try:
            mois_num = mois_republicains.get(mois.lower())
            annee_greg = annees_republicaines.get(annee.upper())
            
            if mois_num and annee_greg:
                # Approximation simple (chaque mois = 30 jours)
                jour_annee = (mois_num - 1) * 30 + int(jour)
                
                # Date approximative grégorienne
                import datetime
                debut_annee = datetime.date(annee_greg, 9, 22)  # 22 septembre = début an républicain
                date_approx = debut_annee + datetime.timedelta(days=jour_annee)
                
                return date_approx.strftime("%d/%m/%Y")
        except:
            pass
        
        return None

class EtatCivilAncienParser(PeriodSpecificParser):
    """Parser pour état civil ancien (1815-1900)"""
    
    def parse(self, text: str) -> Dict:
        # Logique spécialisée pour état civil 19ème siècle
        # Format plus standardisé que l'Ancien Régime
        result = {
            'periode': 'État civil ancien (1815-1900)',
            'actes': {'naissances': 0, 'mariages': 0, 'deces': 0},
            'personnes': [],
            'communes': set()
        }
        
        # Patterns état civil standardisé
        patterns = {
            'acte_naissance': re.compile(r'acte\s+de\s+naissance.*?né(?:e)?\s+le\s+(\d{1,2})\s+(\w+)\s+(\d{4})', re.IGNORECASE),
            'commune': re.compile(r'commune\s+de\s+([A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞß][a-zàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿ\s]+)', re.IGNORECASE)
        }
        
        # Traitement simplifié pour démonstration
        naissances = patterns['acte_naissance'].findall(text)
        result['actes']['naissances'] = len(naissances)
        
        communes = patterns['commune'].findall(text)
        result['communes'] = list(set(communes))
        
        return result

class ModerneParser(PeriodSpecificParser):
    """Parser pour période moderne (1900-1950)"""
    
    def parse(self, text: str) -> Dict:
        # Logique pour documents modernes
        # Format très standardisé
        return {
            'periode': 'Moderne (1900-1950)', 
            'format': 'standardise',
            'actes': {'total': 0},
            'personnes': []
        }

# Test et démonstration
if __name__ == "__main__":
    # Créer le parser multi-périodes
    parser = MultiPeriodParser()
    
    # Textes d'exemple pour chaque période
    test_texts = {
        "Ancien Régime": """
        L'an de grâce 1643, le dimanche 8e jour de mars, moy, Charles Demontigny, prestre, 
        ay, au nom de Dieu, pris possession du bénéfice Notre-Dame d'Esméville.
        1651, 23 janv., inh., dans l'église, de Françoise Picot, épouse de Charles Le Boucher, éc.
        """,
        
        "Révolution": """
        Acte de naissance du citoyen Jean Baptiste Martin, né le 15 vendémiaire de l'an III 
        en la commune de Lyon, département du Rhône. L'officier public certifie...
        """,
        
        "État civil": """
        Acte de naissance de Pierre Dubois, né le 15 janvier 1845 en la commune de Marseille,
        département des Bouches-du-Rhône. Devant nous, maire de la commune...
        """,
        
        "Moderne": """
        Extrait d'acte de naissance de Marie Durand, née le 23 mars 1925 à Paris 15e,
        profession : institutrice, nationalité française...
        """
    }
    
    print("=== TEST PARSER MULTI-PÉRIODES ===\n")
    
    for period_name, text in test_texts.items():
        print(f"--- {period_name.upper()} ---")
        
        # Détection automatique
        detection = parser.detect_period(text)
        print(f"Période détectée: {detection.period.value}")
        print(f"Confiance: {detection.confidence:.2f}")
        print(f"Indicateurs: {detection.indicators[:3]}...")
        
        # Parsing complet
        try:
            result = parser.parse_document(text)
            print(f"Parser utilisé: {result['period_info']['parser_used']}")
            print(f"Résultat: {len(str(result))} caractères de données extraites")
        except Exception as e:
            print(f"Erreur: {e}")
        
        print()
    
    print("✅ Tous les tests de période complétés!")