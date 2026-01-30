"""Tests for forgery detection functionality."""

import pytest
import asyncio
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from document_forensics.analysis.forgery_detector import ForgeryDetector
from document_forensics.core.models import ForgeryType, RiskLevel, DocumentType


class TestForgeryDetector:
    """Test suite for ForgeryDetector."""
    
    @pytest.fixture
    def detector(self):
        """Create forgery detector instance."""
        return ForgeryDetector()
    
    @pytest.mark.asyncio
    async def test_detector_initialization(self, detector):
        """Test forgery detector initializes correctly."""
        assert detector is not None
        assert hasattr(detector, 'format_detectors')
        assert len(detector.format_detectors) == 5
    
    @pytest.mark.asyncio
    async def test_determine_document_type(self, detector):
        """Test document type determination."""
        assert detector._determine_document_type('.docx') == 'word'
        assert detector._determine_document_type('.xlsx') == 'excel'
        assert detector._determine_document_type('.txt') == 'text'
        assert detector._determine_document_type('.jpg') == 'image'
        assert detector._determine_document_type('.pdf') == 'pdf'
        assert detector._determine_document_type('.unknown') == 'unknown'
    
    @pytest.mark.asyncio
    async def test_calculate_overall_risk(self, detector):
        """Test risk calculation."""
        # No indicators
        assert detector._calculate_overall_risk([]) == 'LOW'
        
        # One critical indicator
        indicators = [{'severity': 'CRITICAL', 'confidence': 0.9}]
        assert detector._calculate_overall_risk(indicators) == 'CRITICAL'
        
        # Multiple high indicators
        indicators = [
            {'severity': 'HIGH', 'confidence': 0.8},
            {'severity': 'HIGH', 'confidence': 0.7}
        ]
        assert detector._calculate_overall_risk(indicators) == 'CRITICAL'
        
        # One high indicator
        indicators = [{'severity': 'HIGH', 'confidence': 0.8}]
        assert detector._calculate_overall_risk(indicators) == 'HIGH'
        
        # Multiple medium indicators
        indicators = [
            {'severity': 'MEDIUM', 'confidence': 0.6},
            {'severity': 'MEDIUM', 'confidence': 0.5},
            {'severity': 'MEDIUM', 'confidence': 0.7}
        ]
        assert detector._calculate_overall_risk(indicators) == 'HIGH'
    
    @pytest.mark.asyncio
    async def test_calculate_confidence(self, detector):
        """Test confidence calculation."""
        # No indicators
        assert detector._calculate_confidence([]) == 0.0
        
        # Single indicator
        indicators = [{'severity': 'HIGH', 'confidence': 0.8}]
        confidence = detector._calculate_confidence(indicators)
        assert 0.0 <= confidence <= 1.0
        
        # Multiple indicators
        indicators = [
            {'severity': 'HIGH', 'confidence': 0.8},
            {'severity': 'MEDIUM', 'confidence': 0.6},
            {'severity': 'LOW', 'confidence': 0.4}
        ]
        confidence = detector._calculate_confidence(indicators)
        assert 0.0 <= confidence <= 1.0
    
    @pytest.mark.asyncio
    async def test_create_indicator(self, detector):
        """Test indicator creation."""
        indicator = detector._create_indicator(
            type='HIDDEN_TEXT',
            description='Test hidden text',
            confidence=0.9,
            severity='HIGH',
            location={'paragraph': 1},
            evidence={'text': 'hidden'}
        )
        
        assert indicator['type'] == 'HIDDEN_TEXT'
        assert indicator['description'] == 'Test hidden text'
        assert indicator['confidence'] == 0.9
        assert indicator['severity'] == 'HIGH'
        assert indicator['location'] == {'paragraph': 1}
        assert indicator['evidence'] == {'text': 'hidden'}
        assert 'detection_method' in indicator
    
    @pytest.mark.asyncio
    async def test_get_methods_used(self, detector):
        """Test extraction of detection methods."""
        indicators = [
            {'detection_method': 'method1'},
            {'detection_method': 'method2'},
            {'detection_method': 'method1'}  # Duplicate
        ]
        
        methods = detector._get_methods_used(indicators)
        assert len(methods) == 2
        assert 'method1' in methods
        assert 'method2' in methods


class TestWordForgeryDetection:
    """Test Word document forgery detection."""
    
    @pytest.fixture
    def detector(self):
        """Create forgery detector instance."""
        return ForgeryDetector()
    
    @pytest.mark.asyncio
    async def test_word_detection_methods_exist(self, detector):
        """Test Word detection methods exist."""
        assert hasattr(detector, '_detect_word_forgery')
        assert hasattr(detector, '_analyze_word_revisions')
        assert hasattr(detector, '_analyze_word_styles')
        assert hasattr(detector, '_analyze_word_fonts')
        assert hasattr(detector, '_detect_hidden_text_word')
        assert hasattr(detector, '_analyze_track_changes')
        assert hasattr(detector, '_analyze_word_xml')


class TestExcelForgeryDetection:
    """Test Excel spreadsheet forgery detection."""
    
    @pytest.fixture
    def detector(self):
        """Create forgery detector instance."""
        return ForgeryDetector()
    
    @pytest.mark.asyncio
    async def test_excel_detection_methods_exist(self, detector):
        """Test Excel detection methods exist."""
        assert hasattr(detector, '_detect_excel_forgery')
        assert hasattr(detector, '_analyze_excel_formulas')
        assert hasattr(detector, '_analyze_cell_values')
        assert hasattr(detector, '_detect_hidden_content_excel')
        assert hasattr(detector, '_analyze_data_validation')
        assert hasattr(detector, '_analyze_excel_macros')
        assert hasattr(detector, '_analyze_number_formats')


class TestTextForgeryDetection:
    """Test text file forgery detection."""
    
    @pytest.fixture
    def detector(self):
        """Create forgery detector instance."""
        return ForgeryDetector()
    
    @pytest.mark.asyncio
    async def test_text_detection_methods_exist(self, detector):
        """Test text detection methods exist."""
        assert hasattr(detector, '_detect_text_forgery')
        assert hasattr(detector, '_analyze_text_encoding')
        assert hasattr(detector, '_detect_invisible_characters')
        assert hasattr(detector, '_analyze_line_endings')
        assert hasattr(detector, '_detect_homoglyphs')


class TestImageForgeryDetection:
    """Test image forgery detection."""
    
    @pytest.fixture
    def detector(self):
        """Create forgery detector instance."""
        return ForgeryDetector()
    
    @pytest.mark.asyncio
    async def test_image_detection_methods_exist(self, detector):
        """Test image detection methods exist."""
        assert hasattr(detector, '_detect_image_forgery')
        assert hasattr(detector, '_detect_cloning')
        assert hasattr(detector, '_analyze_image_noise')
        assert hasattr(detector, '_analyze_compression')
        assert hasattr(detector, '_analyze_lighting')
        assert hasattr(detector, '_analyze_edges')


class TestPDFForgeryDetection:
    """Test PDF forgery detection."""
    
    @pytest.fixture
    def detector(self):
        """Create forgery detector instance."""
        return ForgeryDetector()
    
    @pytest.mark.asyncio
    async def test_pdf_detection_methods_exist(self, detector):
        """Test PDF detection methods exist."""
        assert hasattr(detector, '_detect_pdf_forgery')
        assert hasattr(detector, '_verify_pdf_signatures')
        assert hasattr(detector, '_analyze_incremental_updates')
        assert hasattr(detector, '_analyze_pdf_objects')
        assert hasattr(detector, '_analyze_pdf_text_layer')
        assert hasattr(detector, '_analyze_pdf_forms')


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
