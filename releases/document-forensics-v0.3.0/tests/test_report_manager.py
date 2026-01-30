"""Property-based tests for report generation functionality."""

import json
import tempfile
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any
import pytest
from hypothesis import given, strategies as st, settings, assume, HealthCheck
from uuid import uuid4

from src.document_forensics.reporting.report_manager import ReportManager
from src.document_forensics.core.models import (
    AnalysisResults, MetadataAnalysis, TamperingAnalysis, AuthenticityAnalysis,
    VisualEvidence, ReportFormat, RiskLevel, EvidenceType,
    AuthenticityScore, TamperingAnalysis, Modification, PixelInconsistency,
    MetadataAnomaly, SoftwareSignature, TimestampConsistency, AuditAction
)


class TestReportManager:
    """Property-based tests for report generation."""
    
    @pytest.fixture
    def report_manager(self):
        """Create a report manager instance."""
        return ReportManager()
    
    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for test files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir
    
    def create_sample_analysis_results(
        self,
        document_id: int = 1,
        risk_level: RiskLevel = RiskLevel.LOW,
        confidence_score: float = 0.8,
        include_metadata: bool = True,
        include_tampering: bool = True,
        include_authenticity: bool = True,
        include_visual_evidence: bool = True
    ) -> AnalysisResults:
        """Create sample analysis results for testing."""
        
        # Create metadata analysis if requested
        metadata_analysis = None
        if include_metadata:
            metadata_analysis = MetadataAnalysis(
                document_id=document_id,
                extracted_metadata={'author': 'Test Author', 'creation_date': '2024-01-01'},
                timestamp_consistency=TimestampConsistency(
                    is_consistent=True,
                    anomalies=[],
                    chronological_order=True,
                    time_gaps=[]
                ),
                software_signatures=[
                    SoftwareSignature(
                        software_name='Test Software',
                        version='1.0',
                        confidence=0.9,
                        signature_type='metadata',
                        detection_method='pattern_matching'
                    )
                ],
                anomalies=[
                    MetadataAnomaly(
                        anomaly_type='timestamp_inconsistency',
                        description='Minor timestamp discrepancy',
                        severity=RiskLevel.LOW,
                        affected_fields=['creation_date'],
                        confidence=0.6
                    )
                ]
            )
        
        # Create tampering analysis if requested
        tampering_analysis = None
        if include_tampering:
            tampering_analysis = TamperingAnalysis(
                document_id=document_id,
                overall_risk=risk_level,
                detected_modifications=[
                    Modification(
                        type='text_modification',
                        location={'page': 1, 'line': 5},
                        description='Potential text insertion detected',
                        confidence=0.7
                    )
                ],
                pixel_inconsistencies=[
                    PixelInconsistency(
                        region_coordinates={'x': 100, 'y': 200, 'width': 50, 'height': 30},
                        inconsistency_type='noise_anomaly',
                        confidence=0.6,
                        analysis_method='noise_pattern_analysis'
                    )
                ],
                confidence_score=confidence_score
            )
        
        # Create authenticity analysis if requested
        authenticity_analysis = None
        if include_authenticity:
            authenticity_analysis = AuthenticityAnalysis(
                document_id=document_id,
                authenticity_score=AuthenticityScore(
                    overall_score=confidence_score,
                    confidence_level=0.85,
                    contributing_factors={
                        'format_consistency': 0.9,
                        'metadata_authenticity': 0.8,
                        'content_integrity': 0.85
                    },
                    risk_assessment=risk_level
                )
            )
        
        # Create visual evidence if requested
        visual_evidence = []
        if include_visual_evidence:
            visual_evidence = [
                VisualEvidence(
                    type=EvidenceType.TAMPERING_HEATMAP,
                    description='Tampering heatmap showing suspicious regions',
                    confidence_level=0.8,
                    analysis_method='computer_vision_analysis'
                )
            ]
        
        return AnalysisResults(
            document_id=document_id,
            metadata_analysis=metadata_analysis,
            tampering_analysis=tampering_analysis,
            authenticity_analysis=authenticity_analysis,
            visual_evidence=visual_evidence,
            overall_risk_assessment=risk_level,
            confidence_score=confidence_score,
            processing_time=2.5
        )
    
    @given(
        document_id=st.integers(min_value=1, max_value=1000),
        risk_level=st.sampled_from(list(RiskLevel)),
        confidence_score=st.floats(min_value=0.0, max_value=1.0),
        report_format=st.sampled_from(list(ReportFormat))
    )
    @settings(max_examples=15, deadline=30000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @pytest.mark.asyncio
    async def test_property_comprehensive_report_generation(
        self, report_manager, temp_dir, document_id, risk_level, confidence_score, report_format
    ):
        """
        **Feature: document-forensics, Property 6: Comprehensive Report Generation**
        **Validates: Requirements 5.1, 5.2, 5.3, 5.4, 5.5**
        
        For any completed analysis, the system should generate reports containing all 
        findings, visual evidence, confidence scores, technical details, and be 
        exportable in multiple formats.
        """
        # Create comprehensive analysis results
        analysis_results = self.create_sample_analysis_results(
            document_id=document_id,
            risk_level=risk_level,
            confidence_score=confidence_score,
            include_metadata=True,
            include_tampering=True,
            include_authenticity=True,
            include_visual_evidence=True
        )
        
        # Generate report
        report_content = await report_manager.generate_report(
            analysis_results=analysis_results,
            report_format=report_format,
            include_visual_evidence=True,
            include_technical_details=True
        )
        
        # Verify report was generated
        assert isinstance(report_content, bytes)
        assert len(report_content) > 0
        
        # Verify format-specific requirements
        if report_format == ReportFormat.JSON:
            # Should be valid JSON
            report_data = json.loads(report_content.decode('utf-8'))
            
            # Should contain all findings
            assert 'document_id' in report_data
            assert report_data['document_id'] == document_id
            assert 'confidence_score' in report_data
            assert report_data['confidence_score'] == confidence_score
            assert 'overall_risk_assessment' in report_data
            assert report_data['overall_risk_assessment'] == risk_level.value
            
            # Should contain analysis sections
            assert 'metadata_analysis' in report_data
            assert 'tampering_analysis' in report_data
            assert 'authenticity_analysis' in report_data
            assert 'visual_evidence' in report_data
            
            # Should contain technical details
            assert 'timestamp' in report_data
            assert 'processing_time' in report_data
            
            # Should have report metadata
            assert 'report_metadata' in report_data
            assert report_data['report_metadata']['format'] == 'json'
            
        elif report_format == ReportFormat.XML:
            # Should be valid XML
            root = ET.fromstring(report_content.decode('utf-8'))
            assert root.tag == 'ForensicAnalysisReport'
            
            # Should contain document info
            doc_info = root.find('DocumentInfo')
            assert doc_info is not None
            assert doc_info.find('DocumentId').text == str(document_id)
            assert doc_info.find('ConfidenceScore').text == str(confidence_score)
            assert doc_info.find('OverallRisk').text == risk_level.value
            
            # Should contain analysis sections
            assert root.find('MetadataAnalysis') is not None
            assert root.find('TamperingAnalysis') is not None
            assert root.find('AuthenticityAnalysis') is not None
            assert root.find('VisualEvidence') is not None
            
        elif report_format == ReportFormat.PDF:
            # Should be PDF content (starts with PDF header)
            assert report_content.startswith(b'%PDF-')
            # Should have reasonable size for a comprehensive report
            assert len(report_content) > 1000  # At least 1KB for a real report
    
    @given(
        num_analyses=st.integers(min_value=1, max_value=5),
        include_components=st.lists(st.booleans(), min_size=4, max_size=4)
    )
    @settings(max_examples=10, deadline=25000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @pytest.mark.asyncio
    async def test_property_report_content_completeness(
        self, report_manager, temp_dir, num_analyses, include_components
    ):
        """
        Test that reports contain all requested components and findings
        regardless of the specific analysis configuration.
        """
        include_metadata, include_tampering, include_authenticity, include_visual = include_components
        
        # Ensure at least one analysis component is included to satisfy validation
        if not any([include_metadata, include_tampering, include_authenticity]):
            include_metadata = True  # Force metadata analysis to be included
        
        # Create analysis results with varying components
        analysis_results = self.create_sample_analysis_results(
            document_id=1,
            include_metadata=include_metadata,
            include_tampering=include_tampering,
            include_authenticity=include_authenticity,
            include_visual_evidence=include_visual
        )
        
        # Generate JSON report for easy parsing
        report_content = await report_manager.generate_report(
            analysis_results=analysis_results,
            report_format=ReportFormat.JSON,
            include_visual_evidence=True,
            include_technical_details=True
        )
        
        report_data = json.loads(report_content.decode('utf-8'))
        
        # Verify presence/absence of components matches input
        if include_metadata:
            assert report_data['metadata_analysis'] is not None
            assert 'software_signatures' in report_data['metadata_analysis']
            assert 'anomalies' in report_data['metadata_analysis']
        else:
            assert report_data['metadata_analysis'] is None
        
        if include_tampering:
            assert report_data['tampering_analysis'] is not None
            assert 'overall_risk' in report_data['tampering_analysis']
            assert 'detected_modifications' in report_data['tampering_analysis']
        else:
            assert report_data['tampering_analysis'] is None
        
        if include_authenticity:
            assert report_data['authenticity_analysis'] is not None
            assert 'authenticity_score' in report_data['authenticity_analysis']
        else:
            assert report_data['authenticity_analysis'] is None
        
        if include_visual:
            assert isinstance(report_data['visual_evidence'], list)
            assert len(report_data['visual_evidence']) > 0
        else:
            assert len(report_data['visual_evidence']) == 0
        
        # Should always contain core document information
        assert 'document_id' in report_data
        assert 'timestamp' in report_data
        assert 'confidence_score' in report_data
        assert 'overall_risk_assessment' in report_data
    
    @given(
        confidence_scores=st.lists(
            st.floats(min_value=0.0, max_value=1.0),
            min_size=2,
            max_size=10
        ),
        risk_levels=st.lists(
            st.sampled_from(list(RiskLevel)),
            min_size=2,
            max_size=10
        )
    )
    @settings(max_examples=8, deadline=20000, suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.filter_too_much])
    @pytest.mark.asyncio
    async def test_property_statistical_summary_accuracy(
        self, report_manager, confidence_scores, risk_levels
    ):
        """
        Test that statistical summaries accurately reflect the input data
        and provide meaningful statistical measures.
        """
        assume(len(confidence_scores) == len(risk_levels))
        
        # Create multiple analysis results
        analysis_results_list = []
        for i, (confidence, risk) in enumerate(zip(confidence_scores, risk_levels)):
            analysis_results = self.create_sample_analysis_results(
                document_id=i+1,
                confidence_score=confidence,
                risk_level=risk
            )
            analysis_results_list.append(analysis_results)
        
        # Generate statistical summary
        summary = await report_manager.generate_statistical_summary(analysis_results_list)
        
        # Verify summary structure
        assert isinstance(summary, dict)
        assert 'total_documents' in summary
        assert summary['total_documents'] == len(analysis_results_list)
        
        # Verify confidence statistics
        assert 'confidence_statistics' in summary
        conf_stats = summary['confidence_statistics']
        
        # Check statistical accuracy
        import numpy as np
        expected_mean = np.mean(confidence_scores)
        expected_median = np.median(confidence_scores)
        expected_std = np.std(confidence_scores)
        expected_min = np.min(confidence_scores)
        expected_max = np.max(confidence_scores)
        
        assert abs(conf_stats['mean'] - expected_mean) < 1e-10
        assert abs(conf_stats['median'] - expected_median) < 1e-10
        assert abs(conf_stats['std_dev'] - expected_std) < 1e-10
        assert abs(conf_stats['min'] - expected_min) < 1e-10
        assert abs(conf_stats['max'] - expected_max) < 1e-10
        
        # Verify risk distribution
        assert 'risk_distribution' in summary
        risk_dist = summary['risk_distribution']
        
        # Check risk level counts
        for risk_level in set(risk_levels):
            expected_count = risk_levels.count(risk_level.value)
            assert risk_dist.get(risk_level.value, 0) == expected_count
        
        # Verify processing statistics
        assert 'processing_statistics' in summary
        assert 'analysis_coverage' in summary
    
    @given(
        num_visual_evidence=st.integers(min_value=0, max_value=5),
        evidence_types=st.lists(
            st.sampled_from(list(EvidenceType)),
            min_size=0,
            max_size=5
        )
    )
    @settings(max_examples=8, deadline=15000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @pytest.mark.asyncio
    async def test_property_visual_evidence_compilation(
        self, report_manager, temp_dir, num_visual_evidence, evidence_types
    ):
        """
        Test that visual evidence compilation handles various numbers and types
        of evidence items correctly.
        """
        assume(len(evidence_types) >= num_visual_evidence or num_visual_evidence == 0)
        
        # Create visual evidence list
        visual_evidence_list = []
        for i in range(num_visual_evidence):
            evidence_type = evidence_types[i] if i < len(evidence_types) else EvidenceType.TAMPERING_HEATMAP
            
            evidence = VisualEvidence(
                type=evidence_type,
                description=f'Test evidence {i+1} of type {evidence_type.value}',
                confidence_level=0.8,
                analysis_method='test_method'
            )
            visual_evidence_list.append(evidence)
        
        # Create compilation
        output_path = Path(temp_dir) / 'visual_evidence_compilation.png'
        result_path = await report_manager.create_visual_evidence_compilation(
            visual_evidence_list, str(output_path)
        )
        
        # Verify compilation was created
        assert result_path == str(output_path)
        
        if num_visual_evidence > 0:
            # Should create a file
            assert output_path.exists()
            assert output_path.stat().st_size > 0
        else:
            # May or may not create file for empty evidence list
            # This is acceptable behavior
            pass
    
    @given(
        action_types=st.lists(
            st.sampled_from(['upload', 'analysis_start', 'analysis_complete', 'hash_verification', 'integrity_check', 'document_access']),
            min_size=1,
            max_size=10
        )
    )
    @settings(max_examples=8, deadline=15000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @pytest.mark.asyncio
    async def test_property_chain_of_custody_documentation(
        self, report_manager, action_types
    ):
        """
        Test that chain of custody documentation properly categorizes and
        organizes audit actions chronologically.
        """
        
        # Create audit actions
        audit_actions = []
        base_time = datetime.now(timezone.utc)
        
        for i, action_type in enumerate(action_types):
            action = AuditAction(
                timestamp=base_time.replace(second=i),  # Ensure chronological order
                user_id=f'user_{i}',
                action=action_type,
                details={'step': i},
                ip_address='192.168.1.1',
                document_id=1
            )
            audit_actions.append(action)
        
        # Generate chain of custody documentation
        custody_doc = await report_manager.document_chain_of_custody(
            document_id=1,
            audit_actions=audit_actions
        )
        
        # Verify structure
        assert isinstance(custody_doc, dict)
        assert 'document_id' in custody_doc
        assert custody_doc['document_id'] == 1
        assert 'chain_of_custody' in custody_doc
        assert 'integrity_checkpoints' in custody_doc
        assert 'access_log' in custody_doc
        assert 'generated_at' in custody_doc
        
        # Verify categorization
        chain_actions = ['upload', 'analysis_start', 'analysis_complete']
        integrity_actions = ['hash_verification', 'integrity_check']
        
        chain_count = sum(1 for action in action_types if action in chain_actions)
        integrity_count = sum(1 for action in action_types if action in integrity_actions)
        other_count = sum(1 for action in action_types if action not in chain_actions + integrity_actions)
        
        assert len(custody_doc['chain_of_custody']) == chain_count
        assert len(custody_doc['integrity_checkpoints']) == integrity_count
        assert len(custody_doc['access_log']) == other_count
        
        # Verify chronological order in each category
        for category in ['chain_of_custody', 'integrity_checkpoints', 'access_log']:
            entries = custody_doc[category]
            if len(entries) > 1:
                timestamps = [entry['timestamp'] for entry in entries]
                assert timestamps == sorted(timestamps)  # Should be chronologically ordered
    
    @pytest.mark.asyncio
    async def test_property_error_handling_robustness(self, report_manager, temp_dir):
        """
        Test that report generation handles various error conditions gracefully
        and provides meaningful error messages.
        """
        # Test with minimal analysis results
        metadata_analysis = MetadataAnalysis(
            document_id=1,
            extracted_metadata={'test': 'data'}
        )
        
        minimal_results = AnalysisResults(
            document_id=1,
            overall_risk_assessment=RiskLevel.LOW,
            confidence_score=0.5,
            metadata_analysis=metadata_analysis
        )
        
        # Should handle minimal data without crashing
        for report_format in ReportFormat:
            try:
                report_content = await report_manager.generate_report(
                    analysis_results=minimal_results,
                    report_format=report_format
                )
                assert isinstance(report_content, bytes)
                assert len(report_content) > 0
            except Exception as e:
                # If it fails, should be a meaningful error
                assert isinstance(e, (ValueError, TypeError, AttributeError))
        
        # Test statistical summary with empty list
        empty_summary = await report_manager.generate_statistical_summary([])
        assert isinstance(empty_summary, dict)
        # Should return empty dict or handle gracefully
        
        # Test chain of custody with empty actions
        empty_custody = await report_manager.document_chain_of_custody(1, [])
        assert isinstance(empty_custody, dict)


# Unit tests for specific edge cases and examples
class TestReportManager_Units:
    """Unit tests for specific report generation scenarios."""
    
    @pytest.fixture
    def report_manager(self):
        """Create a report manager instance."""
        return ReportManager()
    
    @pytest.mark.asyncio
    async def test_json_report_structure(self, report_manager):
        """Test JSON report structure with known data."""
        # Create minimal metadata analysis to satisfy validation
        metadata_analysis = MetadataAnalysis(
            document_id=123,
            extracted_metadata={'test': 'data'}
        )
        
        analysis_results = AnalysisResults(
            document_id=123,
            overall_risk_assessment=RiskLevel.MEDIUM,
            confidence_score=0.75,
            processing_time=3.2,
            metadata_analysis=metadata_analysis
        )
        
        report_content = await report_manager.generate_report(
            analysis_results, ReportFormat.JSON
        )
        
        report_data = json.loads(report_content.decode('utf-8'))
        
        # Verify specific structure
        assert report_data['document_id'] == 123
        assert report_data['overall_risk_assessment'] == 'medium'
        assert report_data['confidence_score'] == 0.75
        assert report_data['processing_time'] == 3.2
        assert 'report_metadata' in report_data
        assert report_data['report_metadata']['format'] == 'json'
    
    @pytest.mark.asyncio
    async def test_xml_report_structure(self, report_manager):
        """Test XML report structure with known data."""
        # Create minimal metadata analysis to satisfy validation
        metadata_analysis = MetadataAnalysis(
            document_id=456,
            extracted_metadata={'test': 'data'}
        )
        
        analysis_results = AnalysisResults(
            document_id=456,
            overall_risk_assessment=RiskLevel.HIGH,
            confidence_score=0.9,
            metadata_analysis=metadata_analysis
        )
        
        report_content = await report_manager.generate_report(
            analysis_results, ReportFormat.XML
        )
        
        root = ET.fromstring(report_content.decode('utf-8'))
        
        # Verify specific structure
        assert root.tag == 'ForensicAnalysisReport'
        doc_info = root.find('DocumentInfo')
        assert doc_info.find('DocumentId').text == '456'
        assert doc_info.find('OverallRisk').text == 'high'
        assert doc_info.find('ConfidenceScore').text == '0.9'
    
    @pytest.mark.asyncio
    async def test_pdf_report_generation(self, report_manager):
        """Test PDF report generation with basic validation."""
        # Create minimal metadata analysis to satisfy validation
        metadata_analysis = MetadataAnalysis(
            document_id=789,
            extracted_metadata={'test': 'data'}
        )
        
        analysis_results = AnalysisResults(
            document_id=789,
            overall_risk_assessment=RiskLevel.LOW,
            confidence_score=0.95,
            metadata_analysis=metadata_analysis
        )
        
        report_content = await report_manager.generate_report(
            analysis_results, ReportFormat.PDF
        )
        
        # Basic PDF validation
        assert report_content.startswith(b'%PDF-')
        assert b'Document Forensics Analysis Report' in report_content or len(report_content) > 1000
    
    def test_statistical_calculations(self, report_manager):
        """Test statistical calculation accuracy."""
        import asyncio
        
        # Create test data with known statistics
        confidence_scores = [0.1, 0.5, 0.9]  # Mean: 0.5, Std: ~0.4
        
        analysis_results = []
        for i, score in enumerate(confidence_scores):
            # Create minimal metadata analysis to satisfy validation
            metadata_analysis = MetadataAnalysis(
                document_id=i,
                extracted_metadata={'test': 'data'}
            )
            
            result = AnalysisResults(
                document_id=i,
                confidence_score=score,
                overall_risk_assessment=RiskLevel.LOW,
                processing_time=float(i + 1),
                metadata_analysis=metadata_analysis
            )
            analysis_results.append(result)
        
        summary = asyncio.run(report_manager.generate_statistical_summary(analysis_results))
        
        # Verify calculations
        assert summary['total_documents'] == 3
        assert abs(summary['confidence_statistics']['mean'] - 0.5) < 0.01
        assert summary['confidence_statistics']['min'] == 0.1
        assert summary['confidence_statistics']['max'] == 0.9
        assert summary['processing_statistics']['mean_time'] == 2.0  # (1+2+3)/3