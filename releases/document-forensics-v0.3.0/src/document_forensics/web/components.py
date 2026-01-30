"""Reusable components for the Streamlit web interface."""

import base64
import io
from typing import Dict, Any, List, Optional

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from document_forensics.core.models import RiskLevel, EvidenceType


class VisualEvidenceRenderer:
    """Renders visual evidence with annotations."""
    
    @staticmethod
    def create_heatmap_placeholder(width: int = 400, height: int = 300) -> Image.Image:
        """Create a placeholder heatmap for demonstration."""
        # Create a simple heatmap-like image
        img = Image.new('RGB', (width, height), color='white')
        draw = ImageDraw.Draw(img)
        
        # Add some colored regions to simulate tampering detection
        regions = [
            ((50, 50, 150, 100), 'red', 'High Risk'),
            ((200, 150, 300, 200), 'orange', 'Medium Risk'),
            ((100, 250, 200, 290), 'yellow', 'Low Risk')
        ]
        
        for (x1, y1, x2, y2), color, label in regions:
            # Draw semi-transparent rectangles
            overlay = Image.new('RGBA', (width, height), (0, 0, 0, 0))
            overlay_draw = ImageDraw.Draw(overlay)
            
            color_map = {
                'red': (255, 0, 0, 100),
                'orange': (255, 165, 0, 100),
                'yellow': (255, 255, 0, 100)
            }
            
            overlay_draw.rectangle([x1, y1, x2, y2], fill=color_map[color])
            img = Image.alpha_composite(img.convert('RGBA'), overlay).convert('RGB')
            
            # Add label
            try:
                font = ImageFont.load_default()
                draw.text((x1, y1-15), label, fill='black', font=font)
            except:
                draw.text((x1, y1-15), label, fill='black')
        
        return img
    
    @staticmethod
    def create_pixel_analysis_placeholder(width: int = 400, height: int = 300) -> Image.Image:
        """Create a placeholder pixel analysis visualization."""
        img = Image.new('RGB', (width, height), color='lightgray')
        draw = ImageDraw.Draw(img)
        
        # Simulate pixel inconsistencies with small colored dots
        np.random.seed(42)  # For consistent results
        for _ in range(20):
            x = np.random.randint(0, width)
            y = np.random.randint(0, height)
            size = np.random.randint(3, 8)
            color = np.random.choice(['red', 'orange', 'yellow'])
            
            color_map = {
                'red': (255, 0, 0),
                'orange': (255, 165, 0),
                'yellow': (255, 255, 0)
            }
            
            draw.ellipse([x-size, y-size, x+size, y+size], fill=color_map[color])
        
        # Add title
        try:
            font = ImageFont.load_default()
            draw.text((10, 10), "Pixel Inconsistencies", fill='black', font=font)
        except:
            draw.text((10, 10), "Pixel Inconsistencies", fill='black')
        
        return img
    
    @staticmethod
    def render_evidence_item(evidence: Dict[str, Any], index: int):
        """Render a single visual evidence item."""
        evidence_type = evidence.get("type", "unknown")
        description = evidence.get("description", "No description")
        confidence = evidence.get("confidence_level", 0.0)
        analysis_method = evidence.get("analysis_method", "Unknown")
        
        with st.expander(f"Evidence {index + 1}: {evidence_type.replace('_', ' ').title()}"):
            col1, col2 = st.columns([2, 1])
            
            with col1:
                # Display placeholder image based on evidence type
                if evidence_type == EvidenceType.TAMPERING_HEATMAP:
                    img = VisualEvidenceRenderer.create_heatmap_placeholder()
                    st.image(img, caption="Tampering Detection Heatmap", use_column_width=True)
                elif evidence_type == EvidenceType.PIXEL_ANALYSIS:
                    img = VisualEvidenceRenderer.create_pixel_analysis_placeholder()
                    st.image(img, caption="Pixel-Level Analysis", use_column_width=True)
                else:
                    # Generic placeholder
                    st.info(f"📷 {evidence_type.replace('_', ' ').title()} visualization would be displayed here")
            
            with col2:
                st.metric("Confidence", f"{confidence:.1%}")
                st.write(f"**Method:** {analysis_method}")
                st.write(f"**Description:** {description}")
                
                # Display annotations if available
                annotations = evidence.get("annotations", [])
                if annotations:
                    st.write("**Annotations:**")
                    for ann in annotations:
                        st.write(f"• {ann.get('description', 'No description')}")


class MetricsDisplay:
    """Display metrics and statistics."""
    
    @staticmethod
    def risk_level_badge(risk_level: str) -> str:
        """Generate HTML for risk level badge."""
        colors = {
            "low": "#28a745",
            "medium": "#ffc107", 
            "high": "#fd7e14",
            "critical": "#dc3545"
        }
        
        color = colors.get(risk_level.lower(), "#6c757d")
        return f"""
        <div style="
            background-color: {color};
            color: white;
            padding: 4px 12px;
            border-radius: 12px;
            display: inline-block;
            font-weight: bold;
            font-size: 0.8em;
        ">
            {risk_level.upper()}
        </div>
        """
    
    @staticmethod
    def confidence_bar(confidence: float, label: str = "Confidence") -> None:
        """Display confidence as a progress bar."""
        st.metric(label, f"{confidence:.1%}")
        st.progress(confidence)
    
    @staticmethod
    def create_summary_chart(data: Dict[str, float]) -> None:
        """Create a summary chart of analysis factors."""
        if not data:
            st.info("No data available for chart")
            return
        
        # Create bar chart
        fig, ax = plt.subplots(figsize=(10, 6))
        
        factors = list(data.keys())
        scores = list(data.values())
        
        bars = ax.bar(factors, scores, color=['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd'])
        
        # Customize chart
        ax.set_ylabel('Score')
        ax.set_title('Analysis Factors')
        ax.set_ylim(0, 1)
        
        # Add value labels on bars
        for bar, score in zip(bars, scores):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height + 0.01,
                   f'{score:.2f}', ha='center', va='bottom')
        
        # Rotate x-axis labels if needed
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        
        st.pyplot(fig)
        plt.close()


class DocumentLibraryTable:
    """Document library table component."""
    
    @staticmethod
    def render_document_table(documents: List[Dict[str, Any]]) -> None:
        """Render a table of documents with actions."""
        if not documents:
            st.info("No documents found")
            return
        
        # Convert to DataFrame for better display
        df = pd.DataFrame(documents)
        
        # Add action buttons
        for index, doc in enumerate(documents):
            col1, col2, col3, col4, col5 = st.columns([3, 2, 2, 1, 2])
            
            with col1:
                st.write(doc.get('filename', 'Unknown'))
            
            with col2:
                status = doc.get('status', 'unknown')
                if status == 'completed':
                    st.success(status.title())
                elif status == 'processing':
                    st.info(status.title())
                elif status == 'failed':
                    st.error(status.title())
                else:
                    st.warning(status.title())
            
            with col3:
                risk = doc.get('risk', 'unknown')
                st.markdown(MetricsDisplay.risk_level_badge(risk), unsafe_allow_html=True)
            
            with col4:
                if st.button("View", key=f"view_{index}"):
                    st.session_state.current_document = doc.get('id')
            
            with col5:
                if st.button("Download", key=f"download_{index}"):
                    st.info("Download functionality would be implemented here")


class BatchProgressDisplay:
    """Batch processing progress display."""
    
    @staticmethod
    def render_batch_progress(batch_status: Dict[str, Any]) -> None:
        """Render batch processing progress."""
        total_docs = batch_status.get("total_documents", 0)
        processed_docs = batch_status.get("processed_documents", 0)
        failed_docs = batch_status.get("failed_documents", 0)
        progress_pct = batch_status.get("progress_percentage", 0.0)
        status = batch_status.get("status", "unknown")
        
        # Progress bar
        st.progress(progress_pct / 100.0)
        
        # Metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total", total_docs)
        
        with col2:
            st.metric("Processed", processed_docs)
        
        with col3:
            st.metric("Failed", failed_docs)
        
        with col4:
            success_rate = ((processed_docs - failed_docs) / max(processed_docs, 1)) * 100
            st.metric("Success Rate", f"{success_rate:.1f}%")
        
        # Status indicator
        if status == "completed":
            st.success("✅ Batch completed!")
        elif status == "processing":
            st.info("🔄 Processing...")
        elif status == "failed":
            st.error("❌ Batch failed")
        else:
            st.warning(f"Status: {status}")


class ReportGenerator:
    """Report generation utilities."""
    
    @staticmethod
    def generate_summary_report(results: Dict[str, Any]) -> str:
        """Generate a text summary report."""
        report_lines = [
            "DOCUMENT FORENSICS ANALYSIS REPORT",
            "=" * 40,
            "",
            f"Document ID: {results.get('document_id', 'Unknown')}",
            f"Analysis Date: {results.get('timestamp', 'Unknown')}",
            f"Processing Time: {results.get('processing_time', 0.0):.2f}s",
            "",
            "SUMMARY",
            "-" * 20,
            f"Overall Risk: {results.get('overall_risk_assessment', 'Unknown').upper()}",
            f"Confidence Score: {results.get('confidence_score', 0.0):.1%}",
            "",
        ]
        
        # Add tampering analysis
        tampering_analysis = results.get("tampering_analysis")
        if tampering_analysis:
            report_lines.extend([
                "TAMPERING ANALYSIS",
                "-" * 20,
                f"Risk Level: {tampering_analysis.get('overall_risk', 'Unknown').upper()}",
                f"Modifications Detected: {len(tampering_analysis.get('detected_modifications', []))}",
                ""
            ])
        
        # Add authenticity analysis
        authenticity_analysis = results.get("authenticity_analysis")
        if authenticity_analysis:
            auth_score = authenticity_analysis.get("authenticity_score", {})
            report_lines.extend([
                "AUTHENTICITY ANALYSIS",
                "-" * 20,
                f"Authenticity Score: {auth_score.get('overall_score', 0.0):.1%}",
                f"Confidence Level: {auth_score.get('confidence_level', 0.0):.1%}",
                ""
            ])
        
        # Add visual evidence summary
        visual_evidence = results.get("visual_evidence", [])
        if visual_evidence:
            report_lines.extend([
                "VISUAL EVIDENCE",
                "-" * 20,
                f"Evidence Items: {len(visual_evidence)}",
                ""
            ])
            
            for i, evidence in enumerate(visual_evidence, 1):
                evidence_type = evidence.get("type", "unknown")
                confidence = evidence.get("confidence_level", 0.0)
                report_lines.append(f"{i}. {evidence_type.replace('_', ' ').title()} (Confidence: {confidence:.1%})")
        
        report_lines.extend([
            "",
            "END OF REPORT",
            "=" * 40
        ])
        
        return "\n".join(report_lines)