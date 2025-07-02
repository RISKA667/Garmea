from .period_parser import PeriodParser, HistoricalPeriod, PeriodDetection
from .strict_parser import StrictParser, ValidatedRelation

try:
    from .pdf_analyzer import PDFAnalyzer, PageAnalysis, ProcessingResult, HAS_PYMUPDF
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False
    PDFAnalyzer = None
    PageAnalysis = None
    ProcessingResult = None
    HAS_PYMUPDF = False

__all__ = [
    'PeriodParser',
    'HistoricalPeriod',
    'PeriodDetection',
    'StrictParser',
    'ValidatedRelation'
]

if PDF_AVAILABLE:
    __all__.extend([
        'PDFAnalyzer',
        'PageAnalysis',
        'ProcessingResult'
    ])

def get_specialized_capabilities():
    return {
        'period_parsing': True,
        'strict_validation': True,
        'pdf_analysis': PDF_AVAILABLE,
        'pymupdf_available': HAS_PYMUPDF if PDF_AVAILABLE else False
    }