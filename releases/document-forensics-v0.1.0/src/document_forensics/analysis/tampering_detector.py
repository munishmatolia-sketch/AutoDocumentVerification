"""Tampering detection component with AI integration for document forensics."""

import io
import logging
from typing import Dict, List, Optional, Tuple, Any
import numpy as np
import cv2
from PIL import Image
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from skimage import feature, measure, segmentation
from skimage.filters import gaussian
from skimage.metrics import structural_similarity as ssim
import spacy
import nltk
from nltk.tokenize import word_tokenize, sent_tokenize
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.exceptions import InvalidSignature
import PyPDF2
from docx import Document as DocxDocument
import json

from ..core.models import (
    TamperingAnalysis, PixelInconsistency, TextModification, 
    SignatureBreak, CompressionAnomaly, Modification, RiskLevel,
    VisualEvidence, EvidenceType, Annotation
)
from ..utils.crypto import hash_document

logger = logging.getLogger(__name__)


class TamperingDetector:
    """AI-powered tampering detection for documents."""
    
    def __init__(self):
        """Initialize the tampering detector with AI models."""
        self.nlp = None
        self._initialize_nlp()
        self._initialize_nltk()
        
    def _initialize_nlp(self):
        """Initialize spaCy NLP model."""
        try:
            self.nlp = spacy.load("en_core_web_sm")
        except OSError:
            logger.warning("spaCy model 'en_core_web_sm' not found. Text analysis will be limited.")
            self.nlp = None
    
    def _initialize_nltk(self):
        """Initialize NLTK data."""
        try:
            nltk.data.find('tokenizers/punkt')
        except LookupError:
            logger.info("Downloading NLTK punkt tokenizer...")
            nltk.download('punkt', quiet=True)
    
    async def detect_tampering(self, document_path: str, document_id: int) -> TamperingAnalysis:
        """
        Perform comprehensive tampering detection on a document.
        
        Args:
            document_path: Path to the document file
            document_id: Document ID for tracking
            
        Returns:
            TamperingAnalysis with all detected tampering indicators
        """
        logger.info(f"Starting tampering detection for document {document_id}")
        
        modifications = []
        pixel_inconsistencies = []
        text_modifications = []
        signature_breaks = []
        compression_anomalies = []
        
        try:
            # Determine file type and apply appropriate analysis
            file_extension = document_path.lower().split('.')[-1]
            
            if file_extension in ['jpg', 'jpeg', 'png', 'bmp', 'tiff']:
                # Image analysis
                pixel_inconsistencies = await self._analyze_image_tampering(document_path)
                compression_anomalies = await self._detect_compression_anomalies(document_path)
                
            elif file_extension == 'pdf':
                # PDF analysis
                text_modifications = await self._analyze_pdf_text_tampering(document_path)
                signature_breaks = await self._verify_pdf_signatures(document_path)
                
            elif file_extension in ['docx', 'doc']:
                # Word document analysis
                text_modifications = await self._analyze_docx_tampering(document_path)
                
            # Convert specific detections to general modifications
            modifications = self._consolidate_modifications(
                pixel_inconsistencies, text_modifications, signature_breaks, compression_anomalies
            )
            
            # Calculate overall risk level
            overall_risk = self._calculate_risk_level(modifications)
            
            # Calculate confidence score
            confidence_score = self._calculate_confidence_score(modifications)
            
            return TamperingAnalysis(
                document_id=document_id,
                overall_risk=overall_risk,
                detected_modifications=modifications,
                pixel_inconsistencies=pixel_inconsistencies,
                text_modifications=text_modifications,
                signature_breaks=signature_breaks,
                compression_anomalies=compression_anomalies,
                confidence_score=confidence_score
            )
            
        except Exception as e:
            logger.error(f"Error during tampering detection: {str(e)}")
            return TamperingAnalysis(
                document_id=document_id,
                overall_risk=RiskLevel.LOW,
                confidence_score=0.0
            )
    
    async def _analyze_image_tampering(self, image_path: str) -> List[PixelInconsistency]:
        """Analyze image for pixel-level tampering using computer vision."""
        inconsistencies = []
        
        try:
            # Load image
            image = cv2.imread(image_path)
            if image is None:
                return inconsistencies
                
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Error Level Analysis (ELA) simulation
            ela_inconsistencies = await self._error_level_analysis(image)
            inconsistencies.extend(ela_inconsistencies)
            
            # Noise analysis
            noise_inconsistencies = await self._analyze_noise_patterns(gray)
            inconsistencies.extend(noise_inconsistencies)
            
            # JPEG compression analysis
            compression_inconsistencies = await self._analyze_jpeg_compression(image_path)
            inconsistencies.extend(compression_inconsistencies)
            
            # Edge detection for splicing
            edge_inconsistencies = await self._detect_edge_inconsistencies(gray)
            inconsistencies.extend(edge_inconsistencies)
            
        except Exception as e:
            logger.error(f"Error in image tampering analysis: {str(e)}")
            
        return inconsistencies
    
    async def _error_level_analysis(self, image: np.ndarray) -> List[PixelInconsistency]:
        """Perform Error Level Analysis to detect tampering."""
        inconsistencies = []
        
        try:
            # Convert to PIL Image for JPEG compression simulation
            pil_image = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
            
            # Save with different quality levels and compare
            buffer1 = io.BytesIO()
            buffer2 = io.BytesIO()
            
            pil_image.save(buffer1, format='JPEG', quality=90)
            pil_image.save(buffer2, format='JPEG', quality=95)
            
            # Reload and compare
            img1 = np.array(Image.open(buffer1))
            img2 = np.array(Image.open(buffer2))
            
            # Calculate difference
            diff = np.abs(img1.astype(float) - img2.astype(float))
            diff_gray = np.mean(diff, axis=2) if len(diff.shape) == 3 else diff
            
            # Find regions with high error levels
            threshold = np.percentile(diff_gray, 95)
            high_error_regions = diff_gray > threshold
            
            # Find connected components
            labeled_regions = measure.label(high_error_regions)
            regions = measure.regionprops(labeled_regions)
            
            for region in regions:
                if region.area > 100:  # Filter small regions
                    bbox = region.bbox
                    inconsistencies.append(PixelInconsistency(
                        region_coordinates={
                            'x': int(bbox[1]),
                            'y': int(bbox[0]),
                            'width': int(bbox[3] - bbox[1]),
                            'height': int(bbox[2] - bbox[0])
                        },
                        inconsistency_type='error_level_anomaly',
                        confidence=min(0.9, region.area / 10000),
                        analysis_method='error_level_analysis'
                    ))
                    
        except Exception as e:
            logger.error(f"Error in ELA analysis: {str(e)}")
            
        return inconsistencies
    
    async def _analyze_noise_patterns(self, gray_image: np.ndarray) -> List[PixelInconsistency]:
        """Analyze noise patterns to detect tampering."""
        inconsistencies = []
        
        try:
            # Apply Gaussian filter to estimate noise
            filtered = gaussian(gray_image, sigma=1.0)
            noise = gray_image.astype(float) - filtered
            
            # Analyze noise variance in different regions
            h, w = gray_image.shape
            block_size = 64
            
            for y in range(0, h - block_size, block_size // 2):
                for x in range(0, w - block_size, block_size // 2):
                    block_noise = noise[y:y+block_size, x:x+block_size]
                    noise_var = np.var(block_noise)
                    
                    # Compare with neighboring blocks
                    neighbor_vars = []
                    for dy in [-block_size, 0, block_size]:
                        for dx in [-block_size, 0, block_size]:
                            if dy == 0 and dx == 0:
                                continue
                            ny, nx = y + dy, x + dx
                            if 0 <= ny < h - block_size and 0 <= nx < w - block_size:
                                neighbor_block = noise[ny:ny+block_size, nx:nx+block_size]
                                neighbor_vars.append(np.var(neighbor_block))
                    
                    if neighbor_vars:
                        avg_neighbor_var = np.mean(neighbor_vars)
                        if noise_var > 2 * avg_neighbor_var and noise_var > 0.01:
                            inconsistencies.append(PixelInconsistency(
                                region_coordinates={
                                    'x': x, 'y': y,
                                    'width': block_size, 'height': block_size
                                },
                                inconsistency_type='noise_anomaly',
                                confidence=min(0.8, (noise_var - avg_neighbor_var) / avg_neighbor_var),
                                analysis_method='noise_pattern_analysis'
                            ))
                            
        except Exception as e:
            logger.error(f"Error in noise pattern analysis: {str(e)}")
            
        return inconsistencies
    
    async def _analyze_jpeg_compression(self, image_path: str) -> List[PixelInconsistency]:
        """Analyze JPEG compression artifacts for tampering detection."""
        inconsistencies = []
        
        try:
            # Load image and analyze DCT coefficients if JPEG
            if not image_path.lower().endswith(('.jpg', '.jpeg')):
                return inconsistencies
                
            image = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
            if image is None:
                return inconsistencies
            
            # Analyze 8x8 blocks for JPEG artifacts
            h, w = image.shape
            block_size = 8
            
            for y in range(0, h - block_size, block_size):
                for x in range(0, w - block_size, block_size):
                    block = image[y:y+block_size, x:x+block_size].astype(float)
                    
                    # Apply DCT
                    dct_block = cv2.dct(block)
                    
                    # Analyze high-frequency components
                    high_freq = np.sum(np.abs(dct_block[4:, 4:]))
                    total_energy = np.sum(np.abs(dct_block))
                    
                    if total_energy > 0:
                        high_freq_ratio = high_freq / total_energy
                        
                        # Unusual high-frequency content might indicate tampering
                        if high_freq_ratio > 0.3:
                            inconsistencies.append(PixelInconsistency(
                                region_coordinates={
                                    'x': x, 'y': y,
                                    'width': block_size, 'height': block_size
                                },
                                inconsistency_type='compression_artifact',
                                confidence=min(0.7, high_freq_ratio),
                                analysis_method='jpeg_compression_analysis'
                            ))
                            
        except Exception as e:
            logger.error(f"Error in JPEG compression analysis: {str(e)}")
            
        return inconsistencies
    
    async def _detect_edge_inconsistencies(self, gray_image: np.ndarray) -> List[PixelInconsistency]:
        """Detect edge inconsistencies that might indicate splicing."""
        inconsistencies = []
        
        try:
            # Apply Canny edge detection
            edges = feature.canny(gray_image, sigma=1.0, low_threshold=0.1, high_threshold=0.2)
            
            # Analyze edge continuity
            labeled_edges = measure.label(edges)
            edge_regions = measure.regionprops(labeled_edges)
            
            for region in edge_regions:
                # Check for abrupt edge terminations
                if region.area > 50:
                    bbox = region.bbox
                    edge_density = region.area / ((bbox[2] - bbox[0]) * (bbox[3] - bbox[1]))
                    
                    # Low edge density might indicate artificial boundaries
                    if edge_density < 0.1:
                        inconsistencies.append(PixelInconsistency(
                            region_coordinates={
                                'x': int(bbox[1]),
                                'y': int(bbox[0]),
                                'width': int(bbox[3] - bbox[1]),
                                'height': int(bbox[2] - bbox[0])
                            },
                            inconsistency_type='edge_discontinuity',
                            confidence=0.6,
                            analysis_method='edge_consistency_analysis'
                        ))
                        
        except Exception as e:
            logger.error(f"Error in edge inconsistency detection: {str(e)}")
            
        return inconsistencies
    
    async def _detect_compression_anomalies(self, image_path: str) -> List[CompressionAnomaly]:
        """Detect compression anomalies in images."""
        anomalies = []
        
        try:
            image = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
            if image is None:
                return anomalies
            
            # Analyze compression ratios in different regions
            h, w = image.shape
            block_size = 128
            
            for y in range(0, h - block_size, block_size // 2):
                for x in range(0, w - block_size, block_size // 2):
                    block = image[y:y+block_size, x:x+block_size]
                    
                    # Estimate compression ratio using entropy
                    hist, _ = np.histogram(block, bins=256, range=(0, 256))
                    hist = hist / np.sum(hist)
                    entropy = -np.sum(hist * np.log2(hist + 1e-10))
                    
                    # Compare with expected entropy for natural images
                    expected_entropy = 7.5  # Typical for natural images
                    entropy_diff = abs(entropy - expected_entropy)
                    
                    if entropy_diff > 2.0:
                        anomalies.append(CompressionAnomaly(
                            region={'x': x, 'y': y, 'width': block_size, 'height': block_size},
                            anomaly_type='entropy_anomaly',
                            expected_compression=expected_entropy,
                            actual_compression=entropy,
                            confidence=min(0.8, entropy_diff / 3.0)
                        ))
                        
        except Exception as e:
            logger.error(f"Error in compression anomaly detection: {str(e)}")
            
        return anomalies
    
    async def _analyze_pdf_text_tampering(self, pdf_path: str) -> List[TextModification]:
        """Analyze PDF for text tampering."""
        modifications = []
        
        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                
                for page_num, page in enumerate(pdf_reader.pages):
                    text = page.extract_text()
                    
                    # Analyze text for inconsistencies
                    text_mods = await self._analyze_text_consistency(text, page_num)
                    modifications.extend(text_mods)
                    
                    # Check for font inconsistencies (simplified)
                    font_mods = await self._analyze_font_consistency(page, page_num)
                    modifications.extend(font_mods)
                    
        except Exception as e:
            logger.error(f"Error in PDF text tampering analysis: {str(e)}")
            
        return modifications
    
    async def _analyze_docx_tampering(self, docx_path: str) -> List[TextModification]:
        """Analyze DOCX document for tampering."""
        modifications = []
        
        try:
            doc = DocxDocument(docx_path)
            
            # Analyze paragraph consistency
            for para_idx, paragraph in enumerate(doc.paragraphs):
                text = paragraph.text
                if text.strip():
                    text_mods = await self._analyze_text_consistency(text, para_idx)
                    modifications.extend(text_mods)
                    
                    # Check formatting consistency
                    format_mods = await self._analyze_formatting_consistency(paragraph, para_idx)
                    modifications.extend(format_mods)
                    
        except Exception as e:
            logger.error(f"Error in DOCX tampering analysis: {str(e)}")
            
        return modifications
    
    async def _analyze_text_consistency(self, text: str, location_id: int) -> List[TextModification]:
        """Analyze text for linguistic inconsistencies."""
        modifications = []
        
        try:
            if not self.nlp:
                return modifications
                
            # Process text with spaCy
            doc = self.nlp(text)
            
            # Check for unusual patterns
            sentences = list(doc.sents)
            
            for sent_idx, sent in enumerate(sentences):
                # Check sentence structure consistency
                if len(sent) > 5:  # Only analyze substantial sentences
                    # Analyze POS tag patterns
                    pos_pattern = [token.pos_ for token in sent]
                    
                    # Look for unusual patterns that might indicate insertion
                    unusual_patterns = self._detect_unusual_pos_patterns(pos_pattern)
                    
                    if unusual_patterns:
                        modifications.append(TextModification(
                            location={'page': location_id, 'sentence': sent_idx},
                            modification_type='linguistic_anomaly',
                            modified_text=sent.text,
                            confidence=0.6
                        ))
                        
                    # Check for semantic inconsistencies
                    semantic_issues = await self._check_semantic_consistency(sent)
                    if semantic_issues:
                        modifications.append(TextModification(
                            location={'page': location_id, 'sentence': sent_idx},
                            modification_type='semantic_inconsistency',
                            modified_text=sent.text,
                            confidence=0.5
                        ))
                        
        except Exception as e:
            logger.error(f"Error in text consistency analysis: {str(e)}")
            
        return modifications
    
    def _detect_unusual_pos_patterns(self, pos_pattern: List[str]) -> bool:
        """Detect unusual part-of-speech patterns."""
        # Simple heuristics for unusual patterns
        unusual_sequences = [
            ['DET', 'DET'],  # Double determiners
            ['VERB', 'VERB', 'VERB'],  # Triple verbs
            ['ADJ', 'ADJ', 'ADJ', 'ADJ']  # Excessive adjectives
        ]
        
        pattern_str = ' '.join(pos_pattern)
        for unusual in unusual_sequences:
            if ' '.join(unusual) in pattern_str:
                return True
        return False
    
    async def _check_semantic_consistency(self, sentence) -> bool:
        """Check for semantic inconsistencies in a sentence."""
        # Simplified semantic consistency check
        # In a real implementation, this would use more sophisticated NLP models
        
        # Check for contradictory sentiment within the same sentence
        positive_words = {'good', 'great', 'excellent', 'wonderful', 'amazing'}
        negative_words = {'bad', 'terrible', 'awful', 'horrible', 'disgusting'}
        
        tokens = [token.text.lower() for token in sentence]
        has_positive = any(word in positive_words for word in tokens)
        has_negative = any(word in negative_words for word in tokens)
        
        # If both positive and negative sentiment in same sentence, flag as potential issue
        return has_positive and has_negative
    
    async def _analyze_font_consistency(self, page, page_num: int) -> List[TextModification]:
        """Analyze font consistency in PDF page."""
        modifications = []
        
        try:
            # This is a simplified implementation
            # In practice, you'd need to extract font information from PDF objects
            # For now, we'll create a placeholder that could be expanded
            
            # Check if page has font information available
            if hasattr(page, 'get_fonts'):
                fonts = page.get_fonts()
                if len(fonts) > 5:  # Unusual number of fonts might indicate tampering
                    modifications.append(TextModification(
                        location={'page': page_num},
                        modification_type='font_inconsistency',
                        confidence=0.4
                    ))
                    
        except Exception as e:
            logger.error(f"Error in font consistency analysis: {str(e)}")
            
        return modifications
    
    async def _analyze_formatting_consistency(self, paragraph, para_idx: int) -> List[TextModification]:
        """Analyze formatting consistency in document paragraph."""
        modifications = []
        
        try:
            # Check for unusual formatting changes within paragraph
            runs = paragraph.runs
            if len(runs) > 10:  # Many formatting changes might indicate tampering
                font_sizes = []
                font_names = []
                
                for run in runs:
                    if run.font.size:
                        font_sizes.append(run.font.size.pt)
                    if run.font.name:
                        font_names.append(run.font.name)
                
                # Check for unusual variation
                if len(set(font_sizes)) > 3 or len(set(font_names)) > 2:
                    modifications.append(TextModification(
                        location={'paragraph': para_idx},
                        modification_type='formatting_inconsistency',
                        confidence=0.5
                    ))
                    
        except Exception as e:
            logger.error(f"Error in formatting consistency analysis: {str(e)}")
            
        return modifications
    
    async def _verify_pdf_signatures(self, pdf_path: str) -> List[SignatureBreak]:
        """Verify digital signatures in PDF."""
        signature_breaks = []
        
        try:
            # This is a simplified implementation
            # Real PDF signature verification would require more sophisticated libraries
            with open(pdf_path, 'rb') as file:
                content = file.read()
                
                # Look for signature-related keywords in PDF content
                if b'/Sig' in content or b'/ByteRange' in content:
                    # PDF has signatures, but we can't verify them without proper tools
                    # For now, we'll flag this as needing manual verification
                    signature_breaks.append(SignatureBreak(
                        signature_id='pdf_signature_1',
                        break_type='verification_needed',
                        timestamp=None,
                        affected_content='entire_document',
                        verification_status=False
                    ))
                    
        except Exception as e:
            logger.error(f"Error in PDF signature verification: {str(e)}")
            
        return signature_breaks
    
    def _consolidate_modifications(
        self, 
        pixel_inconsistencies: List[PixelInconsistency],
        text_modifications: List[TextModification],
        signature_breaks: List[SignatureBreak],
        compression_anomalies: List[CompressionAnomaly]
    ) -> List[Modification]:
        """Consolidate all detected modifications into a unified list."""
        modifications = []
        
        # Convert pixel inconsistencies
        for pixel in pixel_inconsistencies:
            modifications.append(Modification(
                type='pixel_inconsistency',
                location=pixel.region_coordinates,
                description=f"{pixel.inconsistency_type} detected using {pixel.analysis_method}",
                confidence=pixel.confidence,
                evidence_data={'analysis_method': pixel.analysis_method}
            ))
        
        # Convert text modifications
        for text_mod in text_modifications:
            modifications.append(Modification(
                type='text_modification',
                location=text_mod.location,
                description=f"{text_mod.modification_type} detected",
                confidence=text_mod.confidence,
                evidence_data={
                    'original_text': text_mod.original_text,
                    'modified_text': text_mod.modified_text
                }
            ))
        
        # Convert signature breaks
        for sig_break in signature_breaks:
            modifications.append(Modification(
                type='signature_break',
                location={'signature_id': sig_break.signature_id},
                description=f"Digital signature {sig_break.break_type}",
                confidence=0.8 if not sig_break.verification_status else 0.2,
                evidence_data={'break_type': sig_break.break_type}
            ))
        
        # Convert compression anomalies
        for comp_anom in compression_anomalies:
            modifications.append(Modification(
                type='compression_anomaly',
                location=comp_anom.region,
                description=f"{comp_anom.anomaly_type} detected",
                confidence=comp_anom.confidence,
                evidence_data={
                    'expected_compression': comp_anom.expected_compression,
                    'actual_compression': comp_anom.actual_compression
                }
            ))
        
        return modifications
    
    def _calculate_risk_level(self, modifications: List[Modification]) -> RiskLevel:
        """Calculate overall risk level based on detected modifications."""
        if not modifications:
            return RiskLevel.LOW
        
        high_confidence_mods = [m for m in modifications if m.confidence > 0.7]
        medium_confidence_mods = [m for m in modifications if 0.4 <= m.confidence <= 0.7]
        
        if len(high_confidence_mods) >= 3:
            return RiskLevel.CRITICAL
        elif len(high_confidence_mods) >= 1:
            return RiskLevel.HIGH
        elif len(medium_confidence_mods) >= 3:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW
    
    def _calculate_confidence_score(self, modifications: List[Modification]) -> float:
        """Calculate overall confidence score for tampering detection."""
        if not modifications:
            return 0.0
        
        # Weight confidence scores by the number of modifications
        total_confidence = sum(mod.confidence for mod in modifications)
        avg_confidence = total_confidence / len(modifications)
        
        # Boost confidence if multiple independent methods agree
        method_types = set(mod.type for mod in modifications)
        method_bonus = min(0.2, len(method_types) * 0.05)
        
        return min(1.0, avg_confidence + method_bonus)
    
    async def generate_tampering_heatmap(
        self, 
        document_path: str, 
        tampering_analysis: TamperingAnalysis
    ) -> VisualEvidence:
        """Generate a visual heatmap showing tampering locations."""
        try:
            # For images, create actual heatmap
            if document_path.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp', '.tiff')):
                return await self._generate_image_heatmap(document_path, tampering_analysis)
            else:
                # For other documents, create a summary visualization
                return await self._generate_document_summary_visualization(tampering_analysis)
                
        except Exception as e:
            logger.error(f"Error generating tampering heatmap: {str(e)}")
            # Return empty evidence on error
            return VisualEvidence(
                type=EvidenceType.TAMPERING_HEATMAP,
                description="Error generating heatmap",
                confidence_level=0.0,
                analysis_method="heatmap_generation"
            )
    
    async def _generate_image_heatmap(
        self, 
        image_path: str, 
        tampering_analysis: TamperingAnalysis
    ) -> VisualEvidence:
        """Generate heatmap for image tampering."""
        # Load original image
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError("Could not load image")
        
        # Create heatmap overlay
        heatmap = np.zeros(image.shape[:2], dtype=np.float32)
        
        # Add pixel inconsistencies to heatmap
        for inconsistency in tampering_analysis.pixel_inconsistencies:
            coords = inconsistency.region_coordinates
            x, y = coords['x'], coords['y']
            w, h = coords['width'], coords['height']
            
            # Add weighted region to heatmap
            heatmap[y:y+h, x:x+w] += inconsistency.confidence
        
        # Normalize heatmap
        if heatmap.max() > 0:
            heatmap = heatmap / heatmap.max()
        
        # Create visualization
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 6))
        
        # Original image
        ax1.imshow(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
        ax1.set_title('Original Image')
        ax1.axis('off')
        
        # Heatmap overlay
        ax2.imshow(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
        im = ax2.imshow(heatmap, alpha=0.6, cmap='hot')
        ax2.set_title('Tampering Heatmap')
        ax2.axis('off')
        
        # Add colorbar
        plt.colorbar(im, ax=ax2, label='Tampering Confidence')
        
        # Save to buffer
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
        buffer.seek(0)
        image_data = buffer.getvalue()
        plt.close()
        
        # Create annotations for detected regions
        annotations = []
        for i, inconsistency in enumerate(tampering_analysis.pixel_inconsistencies):
            coords = inconsistency.region_coordinates
            annotations.append(Annotation(
                type='tampering_region',
                coordinates=coords,
                description=f"{inconsistency.inconsistency_type} (confidence: {inconsistency.confidence:.2f})",
                confidence=inconsistency.confidence
            ))
        
        return VisualEvidence(
            type=EvidenceType.TAMPERING_HEATMAP,
            description=f"Tampering heatmap showing {len(tampering_analysis.pixel_inconsistencies)} suspicious regions",
            annotations=annotations,
            confidence_level=tampering_analysis.confidence_score,
            analysis_method="computer_vision_heatmap"
        )
    
    async def _generate_document_summary_visualization(
        self, 
        tampering_analysis: TamperingAnalysis
    ) -> VisualEvidence:
        """Generate summary visualization for non-image documents."""
        # Create a summary chart of detected modifications
        fig, ax = plt.subplots(figsize=(10, 6))
        
        # Count modifications by type
        mod_types = {}
        for mod in tampering_analysis.detected_modifications:
            mod_types[mod.type] = mod_types.get(mod.type, 0) + 1
        
        if mod_types:
            types = list(mod_types.keys())
            counts = list(mod_types.values())
            
            bars = ax.bar(types, counts, color=['red', 'orange', 'yellow', 'blue'][:len(types)])
            ax.set_title('Detected Tampering by Type')
            ax.set_ylabel('Number of Detections')
            ax.set_xlabel('Modification Type')
            
            # Add value labels on bars
            for bar, count in zip(bars, counts):
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height,
                       f'{count}', ha='center', va='bottom')
        else:
            ax.text(0.5, 0.5, 'No tampering detected', 
                   ha='center', va='center', transform=ax.transAxes, fontsize=16)
            ax.set_title('Tampering Analysis Results')
        
        # Save to buffer
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
        buffer.seek(0)
        image_data = buffer.getvalue()
        plt.close()
        
        return VisualEvidence(
            type=EvidenceType.TAMPERING_HEATMAP,
            description=f"Document tampering summary showing {len(tampering_analysis.detected_modifications)} modifications",
            confidence_level=tampering_analysis.confidence_score,
            analysis_method="document_summary_visualization"
        )