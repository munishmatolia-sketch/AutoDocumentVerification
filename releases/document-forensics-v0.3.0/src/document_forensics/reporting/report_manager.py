"""Report generation and management for document forensics."""

import io
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
import xml.etree.ElementTree as ET
from xml.dom import minidom

import pandas as pd
import numpy as np
from jinja2 import Environment, FileSystemLoader, Template
from PIL import Image, ImageDraw, ImageFont
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as RLImage, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

from ..core.models import (
    AnalysisResults, VisualEvidence, ReportFormat, EvidenceType,
    TamperingAnalysis, MetadataAnalysis, AuthenticityAnalysis,
    RiskLevel, AuditAction
)

logger = logging.getLogger(__name__)


class ReportManager:
    """Comprehensive report generation for document forensics."""
    
    def __init__(self, template_dir: Optional[str] = None):
        """
        Initialize the report manager.
        
        Args:
            template_dir: Directory containing Jinja2 templates
        """
        self.template_dir = template_dir or str(Path(__file__).parent / "templates")
        self.jinja_env = self._setup_jinja_environment()
        
    def _setup_jinja_environment(self) -> Environment:
        """Set up Jinja2 environment for template rendering."""
        try:
            # Try to load from template directory
            if Path(self.template_dir).exists():
                return Environment(loader=FileSystemLoader(self.template_dir))
            else:
                # Create in-memory templates if directory doesn't exist
                return Environment(loader=None)
        except Exception as e:
            logger.warning(f"Could not set up template directory: {str(e)}")
            return Environment(loader=None)
    
    async def generate_report(
        self,
        analysis_results: AnalysisResults,
        report_format: ReportFormat,
        output_path: Optional[str] = None,
        include_visual_evidence: bool = True,
        include_technical_details: bool = True
    ) -> bytes:
        """
        Generate comprehensive forensic report.
        
        Args:
            analysis_results: Complete analysis results
            report_format: Desired output format
            output_path: Optional file path to save report
            include_visual_evidence: Whether to include visual evidence
            include_technical_details: Whether to include technical details
            
        Returns:
            Report content as bytes
        """
        logger.info(f"Generating {report_format.value} report for document {analysis_results.document_id}")
        
        try:
            if report_format == ReportFormat.PDF:
                report_content = await self._generate_pdf_report(
                    analysis_results, include_visual_evidence, include_technical_details
                )
            elif report_format == ReportFormat.JSON:
                report_content = await self._generate_json_report(analysis_results)
            elif report_format == ReportFormat.XML:
                report_content = await self._generate_xml_report(analysis_results)
            else:
                raise ValueError(f"Unsupported report format: {report_format}")
            
            # Save to file if path provided
            if output_path:
                with open(output_path, 'wb') as f:
                    f.write(report_content)
                logger.info(f"Report saved to {output_path}")
            
            return report_content
            
        except Exception as e:
            logger.error(f"Error generating report: {str(e)}")
            raise
    
    async def _generate_pdf_report(
        self,
        analysis_results: AnalysisResults,
        include_visual_evidence: bool,
        include_technical_details: bool
    ) -> bytes:
        """Generate PDF report using ReportLab."""
        buffer = io.BytesIO()
        
        # Create PDF document
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=18
        )
        
        # Build story (content)
        story = []
        styles = getSampleStyleSheet()
        
        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            alignment=TA_CENTER
        )
        story.append(Paragraph("Document Forensics Analysis Report", title_style))
        story.append(Spacer(1, 20))
        
        # Executive Summary
        story.append(Paragraph("Executive Summary", styles['Heading2']))
        summary = self._generate_executive_summary(analysis_results)
        story.append(Paragraph(summary, styles['Normal']))
        story.append(Spacer(1, 20))
        
        # Document Information
        story.append(Paragraph("Document Information", styles['Heading2']))
        doc_info = self._generate_document_info_table(analysis_results)
        story.append(doc_info)
        story.append(Spacer(1, 20))
        
        # Analysis Results
        if analysis_results.metadata_analysis:
            story.extend(self._generate_metadata_section(analysis_results.metadata_analysis, styles))
        
        if analysis_results.tampering_analysis:
            story.extend(self._generate_tampering_section(analysis_results.tampering_analysis, styles))
        
        if analysis_results.authenticity_analysis:
            story.extend(self._generate_authenticity_section(analysis_results.authenticity_analysis, styles))
        
        # Visual Evidence
        if include_visual_evidence and analysis_results.visual_evidence:
            story.extend(self._generate_visual_evidence_section(analysis_results.visual_evidence, styles))
        
        # Technical Details
        if include_technical_details:
            story.extend(self._generate_technical_details_section(analysis_results, styles))
        
        # Conclusions and Recommendations
        story.extend(self._generate_conclusions_section(analysis_results, styles))
        
        # Build PDF
        doc.build(story)
        buffer.seek(0)
        return buffer.getvalue()
    
    def _generate_executive_summary(self, analysis_results: AnalysisResults) -> str:
        """Generate executive summary text."""
        risk_level = analysis_results.overall_risk_assessment
        confidence = analysis_results.confidence_score
        
        summary_parts = [
            f"This report presents the results of a comprehensive forensic analysis of document ID {analysis_results.document_id}.",
            f"The overall risk assessment is {risk_level.value.upper()} with a confidence score of {confidence:.2f}."
        ]
        
        # Add specific findings
        if analysis_results.tampering_analysis and analysis_results.tampering_analysis.detected_modifications:
            num_modifications = len(analysis_results.tampering_analysis.detected_modifications)
            summary_parts.append(f"The analysis detected {num_modifications} potential modification(s) to the document.")
        
        if analysis_results.authenticity_analysis:
            auth_score = analysis_results.authenticity_analysis.authenticity_score.overall_score
            summary_parts.append(f"The authenticity assessment yielded a score of {auth_score:.2f}.")
        
        return " ".join(summary_parts)
    
    def _generate_document_info_table(self, analysis_results: AnalysisResults) -> Table:
        """Generate document information table."""
        data = [
            ['Document ID', str(analysis_results.document_id)],
            ['Analysis Date', analysis_results.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')],
            ['Processing Time', f"{analysis_results.processing_time:.2f} seconds" if analysis_results.processing_time else "N/A"],
            ['Overall Risk', analysis_results.overall_risk_assessment.value.title()],
            ['Confidence Score', f"{analysis_results.confidence_score:.2f}"]
        ]
        
        table = Table(data, colWidths=[2*inch, 3*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        return table
    
    def _generate_metadata_section(self, metadata_analysis: MetadataAnalysis, styles) -> List:
        """Generate metadata analysis section."""
        section = []
        
        section.append(Paragraph("Metadata Analysis", styles['Heading2']))
        
        # Summary
        if metadata_analysis.anomalies:
            anomaly_count = len(metadata_analysis.anomalies)
            section.append(Paragraph(f"Found {anomaly_count} metadata anomalies.", styles['Normal']))
        else:
            section.append(Paragraph("No significant metadata anomalies detected.", styles['Normal']))
        
        # Software signatures
        if metadata_analysis.software_signatures:
            section.append(Paragraph("Detected Software Signatures:", styles['Heading3']))
            for sig in metadata_analysis.software_signatures:
                sig_text = f"• {sig.software_name}"
                if sig.version:
                    sig_text += f" (Version: {sig.version})"
                sig_text += f" - Confidence: {sig.confidence:.2f}"
                section.append(Paragraph(sig_text, styles['Normal']))
        
        # Timestamp consistency
        if metadata_analysis.timestamp_consistency:
            section.append(Paragraph("Timestamp Analysis:", styles['Heading3']))
            consistency = metadata_analysis.timestamp_consistency
            status = "Consistent" if consistency.is_consistent else "Inconsistent"
            section.append(Paragraph(f"Timestamp consistency: {status}", styles['Normal']))
            
            if consistency.anomalies:
                section.append(Paragraph("Detected anomalies:", styles['Normal']))
                for anomaly in consistency.anomalies:
                    section.append(Paragraph(f"• {anomaly}", styles['Normal']))
        
        section.append(Spacer(1, 20))
        return section
    
    def _generate_tampering_section(self, tampering_analysis: TamperingAnalysis, styles) -> List:
        """Generate tampering analysis section."""
        section = []
        
        section.append(Paragraph("Tampering Detection Analysis", styles['Heading2']))
        
        # Overall assessment
        risk_text = f"Overall tampering risk: {tampering_analysis.overall_risk.value.upper()}"
        confidence_text = f"Detection confidence: {tampering_analysis.confidence_score:.2f}"
        section.append(Paragraph(f"{risk_text} ({confidence_text})", styles['Normal']))
        
        # Detected modifications
        if tampering_analysis.detected_modifications:
            section.append(Paragraph("Detected Modifications:", styles['Heading3']))
            for i, mod in enumerate(tampering_analysis.detected_modifications, 1):
                mod_text = f"{i}. {mod.type.replace('_', ' ').title()}: {mod.description}"
                mod_text += f" (Confidence: {mod.confidence:.2f})"
                section.append(Paragraph(mod_text, styles['Normal']))
        
        # Pixel inconsistencies
        if tampering_analysis.pixel_inconsistencies:
            section.append(Paragraph(f"Pixel Inconsistencies: {len(tampering_analysis.pixel_inconsistencies)} detected", styles['Heading3']))
        
        # Text modifications
        if tampering_analysis.text_modifications:
            section.append(Paragraph(f"Text Modifications: {len(tampering_analysis.text_modifications)} detected", styles['Heading3']))
        
        # Signature breaks
        if tampering_analysis.signature_breaks:
            section.append(Paragraph("Digital Signature Issues:", styles['Heading3']))
            for sig_break in tampering_analysis.signature_breaks:
                section.append(Paragraph(f"• {sig_break.break_type} in signature {sig_break.signature_id}", styles['Normal']))
        
        section.append(Spacer(1, 20))
        return section
    
    def _generate_authenticity_section(self, authenticity_analysis: AuthenticityAnalysis, styles) -> List:
        """Generate authenticity analysis section."""
        section = []
        
        section.append(Paragraph("Authenticity Assessment", styles['Heading2']))
        
        # Overall score
        auth_score = authenticity_analysis.authenticity_score
        section.append(Paragraph(f"Overall authenticity score: {auth_score.overall_score:.2f}", styles['Normal']))
        section.append(Paragraph(f"Assessment confidence: {auth_score.confidence_level:.2f}", styles['Normal']))
        section.append(Paragraph(f"Risk level: {auth_score.risk_assessment.value.upper()}", styles['Normal']))
        
        # Contributing factors
        if auth_score.contributing_factors:
            section.append(Paragraph("Contributing Factors:", styles['Heading3']))
            for factor, score in auth_score.contributing_factors.items():
                factor_name = factor.replace('_', ' ').title()
                section.append(Paragraph(f"• {factor_name}: {score:.2f}", styles['Normal']))
        
        # Structure validation
        if authenticity_analysis.structure_validation:
            section.append(Paragraph("File Structure Validation:", styles['Heading3']))
            struct_val = authenticity_analysis.structure_validation
            status = "Valid" if struct_val.is_valid else "Invalid"
            section.append(Paragraph(f"Structure status: {status}", styles['Normal']))
            section.append(Paragraph(f"Format compliance: {struct_val.format_compliance:.2f}", styles['Normal']))
            
            if struct_val.violations:
                section.append(Paragraph("Violations found:", styles['Normal']))
                for violation in struct_val.violations:
                    section.append(Paragraph(f"• {violation}", styles['Normal']))
        
        # Comparison results
        if authenticity_analysis.comparison_results:
            section.append(Paragraph("Reference Sample Comparisons:", styles['Heading3']))
            for comp in authenticity_analysis.comparison_results:
                section.append(Paragraph(f"• Sample {comp.reference_id}: {comp.similarity_score:.2f} similarity", styles['Normal']))
        
        section.append(Spacer(1, 20))
        return section
    
    def _generate_visual_evidence_section(self, visual_evidence: List[VisualEvidence], styles) -> List:
        """Generate visual evidence section."""
        section = []
        
        section.append(Paragraph("Visual Evidence", styles['Heading2']))
        section.append(Paragraph(f"Generated {len(visual_evidence)} pieces of visual evidence.", styles['Normal']))
        
        for i, evidence in enumerate(visual_evidence, 1):
            section.append(Paragraph(f"Evidence {i}: {evidence.type.value}", styles['Heading3']))
            section.append(Paragraph(evidence.description, styles['Normal']))
            section.append(Paragraph(f"Confidence: {evidence.confidence_level:.2f}", styles['Normal']))
            section.append(Paragraph(f"Analysis method: {evidence.analysis_method}", styles['Normal']))
            
            # Add annotations if present
            if evidence.annotations:
                section.append(Paragraph("Annotations:", styles['Normal']))
                for annotation in evidence.annotations:
                    section.append(Paragraph(f"• {annotation.description} (Confidence: {annotation.confidence:.2f})", styles['Normal']))
        
        section.append(Spacer(1, 20))
        return section
    
    def _generate_technical_details_section(self, analysis_results: AnalysisResults, styles) -> List:
        """Generate technical details section."""
        section = []
        
        section.append(Paragraph("Technical Details", styles['Heading2']))
        
        # Analysis metadata
        section.append(Paragraph("Analysis Metadata:", styles['Heading3']))
        section.append(Paragraph(f"Document ID: {analysis_results.document_id}", styles['Normal']))
        section.append(Paragraph(f"Analysis timestamp: {analysis_results.timestamp}", styles['Normal']))
        if analysis_results.processing_time:
            section.append(Paragraph(f"Processing time: {analysis_results.processing_time:.2f} seconds", styles['Normal']))
        
        # Detailed findings
        section.append(Paragraph("Detailed Findings:", styles['Heading3']))
        
        findings = []
        if analysis_results.metadata_analysis:
            findings.append(f"Metadata analysis completed with {len(analysis_results.metadata_analysis.anomalies)} anomalies")
        
        if analysis_results.tampering_analysis:
            findings.append(f"Tampering analysis detected {len(analysis_results.tampering_analysis.detected_modifications)} modifications")
        
        if analysis_results.authenticity_analysis:
            auth_score = analysis_results.authenticity_analysis.authenticity_score.overall_score
            findings.append(f"Authenticity assessment score: {auth_score:.3f}")
        
        for finding in findings:
            section.append(Paragraph(f"• {finding}", styles['Normal']))
        
        section.append(Spacer(1, 20))
        return section
    
    def _generate_conclusions_section(self, analysis_results: AnalysisResults, styles) -> List:
        """Generate conclusions and recommendations section."""
        section = []
        
        section.append(Paragraph("Conclusions and Recommendations", styles['Heading2']))
        
        # Overall conclusion
        risk_level = analysis_results.overall_risk_assessment
        confidence = analysis_results.confidence_score
        
        if risk_level == RiskLevel.LOW:
            conclusion = "The document appears to be authentic with no significant signs of tampering detected."
        elif risk_level == RiskLevel.MEDIUM:
            conclusion = "The document shows some indicators that warrant further investigation."
        elif risk_level == RiskLevel.HIGH:
            conclusion = "The document shows significant signs of potential tampering or authenticity issues."
        else:  # CRITICAL
            conclusion = "The document shows strong evidence of tampering or authenticity problems."
        
        section.append(Paragraph(f"Conclusion: {conclusion}", styles['Normal']))
        section.append(Paragraph(f"This assessment is made with {confidence:.2f} confidence.", styles['Normal']))
        
        # Recommendations
        section.append(Paragraph("Recommendations:", styles['Heading3']))
        
        recommendations = []
        if risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
            recommendations.append("Conduct additional forensic analysis using specialized tools")
            recommendations.append("Verify document provenance through alternative means")
            recommendations.append("Consider the document potentially compromised for legal purposes")
        elif risk_level == RiskLevel.MEDIUM:
            recommendations.append("Perform additional verification checks")
            recommendations.append("Cross-reference with known authentic samples if available")
        else:
            recommendations.append("Document appears suitable for intended use")
            recommendations.append("Maintain chain of custody documentation")
        
        for rec in recommendations:
            section.append(Paragraph(f"• {rec}", styles['Normal']))
        
        # Footer
        section.append(Spacer(1, 30))
        footer_style = ParagraphStyle(
            'Footer',
            parent=styles['Normal'],
            fontSize=10,
            alignment=TA_CENTER
        )
        section.append(Paragraph("--- End of Report ---", footer_style))
        section.append(Paragraph(f"Generated on {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}", footer_style))
        
        return section
    
    async def _generate_json_report(self, analysis_results: AnalysisResults) -> bytes:
        """Generate JSON report."""
        # Convert analysis results to dictionary
        report_data = {
            'document_id': analysis_results.document_id,
            'timestamp': analysis_results.timestamp.isoformat(),
            'processing_time': analysis_results.processing_time,
            'confidence_score': analysis_results.confidence_score,
            'overall_risk_assessment': analysis_results.overall_risk_assessment.value,
            'metadata_analysis': self._serialize_metadata_analysis(analysis_results.metadata_analysis),
            'tampering_analysis': self._serialize_tampering_analysis(analysis_results.tampering_analysis),
            'authenticity_analysis': self._serialize_authenticity_analysis(analysis_results.authenticity_analysis),
            'visual_evidence': self._serialize_visual_evidence(analysis_results.visual_evidence),
            'report_metadata': {
                'generated_at': datetime.utcnow().isoformat(),
                'format': 'json',
                'version': '1.0'
            }
        }
        
        return json.dumps(report_data, indent=2, default=str).encode('utf-8')
    
    async def _generate_xml_report(self, analysis_results: AnalysisResults) -> bytes:
        """Generate XML report."""
        root = ET.Element('ForensicAnalysisReport')
        root.set('version', '1.0')
        root.set('generated_at', datetime.utcnow().isoformat())
        
        # Document info
        doc_info = ET.SubElement(root, 'DocumentInfo')
        ET.SubElement(doc_info, 'DocumentId').text = str(analysis_results.document_id)
        ET.SubElement(doc_info, 'Timestamp').text = analysis_results.timestamp.isoformat()
        ET.SubElement(doc_info, 'ProcessingTime').text = str(analysis_results.processing_time)
        ET.SubElement(doc_info, 'ConfidenceScore').text = str(analysis_results.confidence_score)
        ET.SubElement(doc_info, 'OverallRisk').text = analysis_results.overall_risk_assessment.value
        
        # Analysis sections
        if analysis_results.metadata_analysis:
            self._add_metadata_xml(root, analysis_results.metadata_analysis)
        
        if analysis_results.tampering_analysis:
            self._add_tampering_xml(root, analysis_results.tampering_analysis)
        
        if analysis_results.authenticity_analysis:
            self._add_authenticity_xml(root, analysis_results.authenticity_analysis)
        
        if analysis_results.visual_evidence:
            self._add_visual_evidence_xml(root, analysis_results.visual_evidence)
        
        # Convert to pretty XML string
        rough_string = ET.tostring(root, 'utf-8')
        reparsed = minidom.parseString(rough_string)
        return reparsed.toprettyxml(indent="  ").encode('utf-8')
    
    def _serialize_metadata_analysis(self, metadata_analysis: Optional[MetadataAnalysis]) -> Optional[Dict]:
        """Serialize metadata analysis to dictionary."""
        if not metadata_analysis:
            return None
        
        return {
            'extracted_metadata': metadata_analysis.extracted_metadata,
            'timestamp_consistency': {
                'is_consistent': metadata_analysis.timestamp_consistency.is_consistent if metadata_analysis.timestamp_consistency else None,
                'anomalies': metadata_analysis.timestamp_consistency.anomalies if metadata_analysis.timestamp_consistency else []
            } if metadata_analysis.timestamp_consistency else None,
            'software_signatures': [
                {
                    'software_name': sig.software_name,
                    'version': sig.version,
                    'confidence': sig.confidence,
                    'signature_type': sig.signature_type,
                    'detection_method': sig.detection_method
                }
                for sig in metadata_analysis.software_signatures
            ],
            'anomalies': [
                {
                    'type': anomaly.anomaly_type,
                    'description': anomaly.description,
                    'severity': anomaly.severity.value,
                    'confidence': anomaly.confidence
                }
                for anomaly in metadata_analysis.anomalies
            ]
        }
    
    def _serialize_tampering_analysis(self, tampering_analysis: Optional[TamperingAnalysis]) -> Optional[Dict]:
        """Serialize tampering analysis to dictionary."""
        if not tampering_analysis:
            return None
        
        return {
            'overall_risk': tampering_analysis.overall_risk.value,
            'confidence_score': tampering_analysis.confidence_score,
            'detected_modifications': [
                {
                    'type': mod.type,
                    'description': mod.description,
                    'confidence': mod.confidence,
                    'location': mod.location
                }
                for mod in tampering_analysis.detected_modifications
            ],
            'pixel_inconsistencies_count': len(tampering_analysis.pixel_inconsistencies),
            'text_modifications_count': len(tampering_analysis.text_modifications),
            'signature_breaks_count': len(tampering_analysis.signature_breaks),
            'compression_anomalies_count': len(tampering_analysis.compression_anomalies)
        }
    
    def _serialize_authenticity_analysis(self, authenticity_analysis: Optional[AuthenticityAnalysis]) -> Optional[Dict]:
        """Serialize authenticity analysis to dictionary."""
        if not authenticity_analysis:
            return None
        
        return {
            'authenticity_score': {
                'overall_score': authenticity_analysis.authenticity_score.overall_score,
                'confidence_level': authenticity_analysis.authenticity_score.confidence_level,
                'risk_assessment': authenticity_analysis.authenticity_score.risk_assessment.value,
                'contributing_factors': authenticity_analysis.authenticity_score.contributing_factors
            },
            'structure_validation': {
                'is_valid': authenticity_analysis.structure_validation.is_valid if authenticity_analysis.structure_validation else None,
                'format_compliance': authenticity_analysis.structure_validation.format_compliance if authenticity_analysis.structure_validation else None,
                'violations': authenticity_analysis.structure_validation.violations if authenticity_analysis.structure_validation else [],
                'recommendations': authenticity_analysis.structure_validation.recommendations if authenticity_analysis.structure_validation else []
            } if authenticity_analysis.structure_validation else None,
            'comparison_results': [
                {
                    'reference_id': comp.reference_id,
                    'similarity_score': comp.similarity_score,
                    'confidence': comp.confidence,
                    'matching_features': comp.matching_features,
                    'differing_features': comp.differing_features
                }
                for comp in authenticity_analysis.comparison_results
            ]
        }
    
    def _serialize_visual_evidence(self, visual_evidence: List[VisualEvidence]) -> List[Dict]:
        """Serialize visual evidence to list of dictionaries."""
        return [
            {
                'type': evidence.type.value,
                'description': evidence.description,
                'confidence_level': evidence.confidence_level,
                'analysis_method': evidence.analysis_method,
                'created_at': evidence.created_at.isoformat(),
                'annotations_count': len(evidence.annotations)
            }
            for evidence in visual_evidence
        ]
    
    def _add_metadata_xml(self, root: ET.Element, metadata_analysis: MetadataAnalysis):
        """Add metadata analysis to XML."""
        metadata_elem = ET.SubElement(root, 'MetadataAnalysis')
        
        if metadata_analysis.software_signatures:
            signatures_elem = ET.SubElement(metadata_elem, 'SoftwareSignatures')
            for sig in metadata_analysis.software_signatures:
                sig_elem = ET.SubElement(signatures_elem, 'Signature')
                ET.SubElement(sig_elem, 'SoftwareName').text = sig.software_name
                ET.SubElement(sig_elem, 'Version').text = sig.version or ''
                ET.SubElement(sig_elem, 'Confidence').text = str(sig.confidence)
        
        if metadata_analysis.anomalies:
            anomalies_elem = ET.SubElement(metadata_elem, 'Anomalies')
            for anomaly in metadata_analysis.anomalies:
                anomaly_elem = ET.SubElement(anomalies_elem, 'Anomaly')
                ET.SubElement(anomaly_elem, 'Type').text = anomaly.anomaly_type
                ET.SubElement(anomaly_elem, 'Description').text = anomaly.description
                ET.SubElement(anomaly_elem, 'Severity').text = anomaly.severity.value
    
    def _add_tampering_xml(self, root: ET.Element, tampering_analysis: TamperingAnalysis):
        """Add tampering analysis to XML."""
        tampering_elem = ET.SubElement(root, 'TamperingAnalysis')
        ET.SubElement(tampering_elem, 'OverallRisk').text = tampering_analysis.overall_risk.value
        ET.SubElement(tampering_elem, 'ConfidenceScore').text = str(tampering_analysis.confidence_score)
        
        if tampering_analysis.detected_modifications:
            mods_elem = ET.SubElement(tampering_elem, 'DetectedModifications')
            for mod in tampering_analysis.detected_modifications:
                mod_elem = ET.SubElement(mods_elem, 'Modification')
                ET.SubElement(mod_elem, 'Type').text = mod.type
                ET.SubElement(mod_elem, 'Description').text = mod.description
                ET.SubElement(mod_elem, 'Confidence').text = str(mod.confidence)
    
    def _add_authenticity_xml(self, root: ET.Element, authenticity_analysis: AuthenticityAnalysis):
        """Add authenticity analysis to XML."""
        auth_elem = ET.SubElement(root, 'AuthenticityAnalysis')
        
        score_elem = ET.SubElement(auth_elem, 'AuthenticityScore')
        ET.SubElement(score_elem, 'OverallScore').text = str(authenticity_analysis.authenticity_score.overall_score)
        ET.SubElement(score_elem, 'ConfidenceLevel').text = str(authenticity_analysis.authenticity_score.confidence_level)
        ET.SubElement(score_elem, 'RiskAssessment').text = authenticity_analysis.authenticity_score.risk_assessment.value
        
        if authenticity_analysis.structure_validation:
            struct_elem = ET.SubElement(auth_elem, 'StructureValidation')
            ET.SubElement(struct_elem, 'IsValid').text = str(authenticity_analysis.structure_validation.is_valid)
            ET.SubElement(struct_elem, 'FormatCompliance').text = str(authenticity_analysis.structure_validation.format_compliance)
    
    def _add_visual_evidence_xml(self, root: ET.Element, visual_evidence: List[VisualEvidence]):
        """Add visual evidence to XML."""
        evidence_elem = ET.SubElement(root, 'VisualEvidence')
        
        for evidence in visual_evidence:
            item_elem = ET.SubElement(evidence_elem, 'EvidenceItem')
            ET.SubElement(item_elem, 'Type').text = evidence.type.value
            ET.SubElement(item_elem, 'Description').text = evidence.description
            ET.SubElement(item_elem, 'ConfidenceLevel').text = str(evidence.confidence_level)
            ET.SubElement(item_elem, 'AnalysisMethod').text = evidence.analysis_method
    
    async def create_visual_evidence_compilation(
        self,
        visual_evidence_list: List[VisualEvidence],
        output_path: str
    ) -> str:
        """
        Create a compiled visual evidence document.
        
        Args:
            visual_evidence_list: List of visual evidence items
            output_path: Path to save the compilation
            
        Returns:
            Path to the created compilation
        """
        try:
            # Create a figure with subplots for each evidence item
            num_evidence = len(visual_evidence_list)
            if num_evidence == 0:
                return output_path
            
            # Calculate grid dimensions
            cols = min(2, num_evidence)
            rows = (num_evidence + cols - 1) // cols
            
            fig, axes = plt.subplots(rows, cols, figsize=(12, 6*rows))
            if num_evidence == 1:
                axes = [axes]
            elif rows == 1:
                axes = [axes] if cols == 1 else axes
            else:
                axes = axes.flatten()
            
            for i, evidence in enumerate(visual_evidence_list):
                ax = axes[i] if i < len(axes) else None
                if ax is None:
                    break
                
                # Create a text-based representation of the evidence
                ax.text(0.5, 0.7, f"Evidence Type: {evidence.type.value}", 
                       ha='center', va='center', fontsize=12, weight='bold')
                ax.text(0.5, 0.5, f"Description: {evidence.description}", 
                       ha='center', va='center', fontsize=10, wrap=True)
                ax.text(0.5, 0.3, f"Confidence: {evidence.confidence_level:.2f}", 
                       ha='center', va='center', fontsize=10)
                ax.text(0.5, 0.1, f"Method: {evidence.analysis_method}", 
                       ha='center', va='center', fontsize=9)
                
                ax.set_xlim(0, 1)
                ax.set_ylim(0, 1)
                ax.set_title(f"Evidence {i+1}")
                ax.axis('off')
            
            # Hide unused subplots
            for i in range(num_evidence, len(axes)):
                axes[i].axis('off')
            
            plt.tight_layout()
            plt.savefig(output_path, dpi=150, bbox_inches='tight')
            plt.close()
            
            logger.info(f"Visual evidence compilation saved to {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Error creating visual evidence compilation: {str(e)}")
            raise
    
    async def generate_statistical_summary(
        self,
        analysis_results_list: List[AnalysisResults]
    ) -> Dict[str, Any]:
        """
        Generate statistical summary across multiple analysis results.
        
        Args:
            analysis_results_list: List of analysis results to summarize
            
        Returns:
            Statistical summary dictionary
        """
        if not analysis_results_list:
            return {}
        
        try:
            # Extract key metrics
            confidence_scores = [r.confidence_score for r in analysis_results_list]
            risk_levels = [r.overall_risk_assessment.value for r in analysis_results_list]
            processing_times = [r.processing_time for r in analysis_results_list if r.processing_time]
            
            # Calculate statistics
            summary = {
                'total_documents': len(analysis_results_list),
                'confidence_statistics': {
                    'mean': np.mean(confidence_scores),
                    'median': np.median(confidence_scores),
                    'std_dev': np.std(confidence_scores),
                    'min': np.min(confidence_scores),
                    'max': np.max(confidence_scores)
                },
                'risk_distribution': {
                    risk: risk_levels.count(risk) for risk in set(risk_levels)
                },
                'processing_statistics': {
                    'mean_time': np.mean(processing_times) if processing_times else 0,
                    'total_time': np.sum(processing_times) if processing_times else 0,
                    'min_time': np.min(processing_times) if processing_times else 0,
                    'max_time': np.max(processing_times) if processing_times else 0
                },
                'analysis_coverage': {
                    'metadata_analysis': sum(1 for r in analysis_results_list if r.metadata_analysis),
                    'tampering_analysis': sum(1 for r in analysis_results_list if r.tampering_analysis),
                    'authenticity_analysis': sum(1 for r in analysis_results_list if r.authenticity_analysis)
                }
            }
            
            return summary
            
        except Exception as e:
            logger.error(f"Error generating statistical summary: {str(e)}")
            return {}
    
    async def document_chain_of_custody(
        self,
        document_id: int,
        audit_actions: List[AuditAction]
    ) -> Dict[str, Any]:
        """
        Document chain of custody for a document.
        
        Args:
            document_id: Document ID
            audit_actions: List of audit actions for the document
            
        Returns:
            Chain of custody documentation
        """
        try:
            custody_doc = {
                'document_id': document_id,
                'chain_of_custody': [],
                'integrity_checkpoints': [],
                'access_log': [],
                'generated_at': datetime.utcnow().isoformat()
            }
            
            # Process audit actions chronologically
            sorted_actions = sorted(audit_actions, key=lambda x: x.timestamp)
            
            for action in sorted_actions:
                custody_entry = {
                    'timestamp': action.timestamp.isoformat(),
                    'action': action.action,
                    'user_id': action.user_id,
                    'details': action.details,
                    'ip_address': action.ip_address
                }
                
                if action.action in ['upload', 'analysis_start', 'analysis_complete']:
                    custody_doc['chain_of_custody'].append(custody_entry)
                elif action.action in ['hash_verification', 'integrity_check']:
                    custody_doc['integrity_checkpoints'].append(custody_entry)
                else:
                    custody_doc['access_log'].append(custody_entry)
            
            return custody_doc
            
        except Exception as e:
            logger.error(f"Error documenting chain of custody: {str(e)}")
            return {}