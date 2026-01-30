"""Streamlit web interface for document forensics system."""

import asyncio
import io
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

import streamlit as st
import pandas as pd
import requests
from PIL import Image

from document_forensics.core.models import (
    Document, AnalysisResults, ProcessingStatus, 
    RiskLevel, FileType, UploadMetadata
)
from document_forensics.core.config import settings
from document_forensics.web.components import (
    VisualEvidenceRenderer, MetricsDisplay, DocumentLibraryTable,
    BatchProgressDisplay, ReportGenerator
)


class DocumentForensicsWebApp:
    """Streamlit web application for document forensics."""
    
    def __init__(self):
        """Initialize the web application."""
        self.api_base_url = settings.API_BASE_URL
        self.setup_page_config()
        self.setup_session_state()
    
    def setup_page_config(self):
        """Configure Streamlit page settings."""
        st.set_page_config(
            page_title="Document Forensics & Verification",
            page_icon="🔍",
            layout="wide",
            initial_sidebar_state="expanded"
        )
    
    def setup_session_state(self):
        """Initialize session state variables."""
        if 'uploaded_documents' not in st.session_state:
            st.session_state.uploaded_documents = []
        if 'analysis_results' not in st.session_state:
            st.session_state.analysis_results = {}
        if 'current_document' not in st.session_state:
            st.session_state.current_document = None
        if 'auth_token' not in st.session_state:
            st.session_state.auth_token = None
    
    def get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers for API requests."""
        headers = {"Content-Type": "application/json"}
        if st.session_state.auth_token:
            headers["Authorization"] = f"Bearer {st.session_state.auth_token}"
        return headers
    
    def upload_document_to_api(self, file_data: bytes, filename: str, 
                             metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Upload document to the API."""
        try:
            files = {"file": (filename, io.BytesIO(file_data), "application/octet-stream")}
            data = {}
            if metadata:
                data["metadata"] = json.dumps(metadata)
            
            response = requests.post(
                f"{self.api_base_url}/documents/upload",
                files=files,
                data=data,
                headers={"Authorization": f"Bearer {st.session_state.auth_token}"} if st.session_state.auth_token else {}
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return {"success": False, "error": f"Upload failed: {response.text}"}
                
        except Exception as e:
            return {"success": False, "error": f"Upload error: {str(e)}"}
    
    def get_analysis_results(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Get analysis results for a document."""
        try:
            response = requests.get(
                f"{self.api_base_url}/analysis/{document_id}",
                headers=self.get_auth_headers()
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return None
                
        except Exception as e:
            st.error(f"Error fetching analysis results: {str(e)}")
            return None
    
    def start_analysis(self, document_id: int) -> bool:
        """Start analysis for a document."""
        try:
            response = requests.post(
                f"{self.api_base_url}/analysis/start",
                json={"document_id": str(document_id)},
                headers=self.get_auth_headers()
            )
            
            return response.status_code == 200
            
        except Exception as e:
            st.error(f"Error starting analysis: {str(e)}")
            return False
    
    def get_document_status(self, document_id: int) -> Optional[Dict[str, Any]]:
        """Get document processing status."""
        try:
            response = requests.get(
                f"{self.api_base_url}/analysis/{document_id}/status",
                headers=self.get_auth_headers()
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return None
                
        except Exception as e:
            return None
    
    def download_report(self, document_id: str, format: str = "pdf") -> Optional[bytes]:
        """Download analysis report."""
        try:
            response = requests.get(
                f"{self.api_base_url}/reports/{document_id}",
                params={"format": format},
                headers=self.get_auth_headers()
            )
            
            if response.status_code == 200:
                return response.content
            else:
                return None
                
        except Exception as e:
            st.error(f"Error downloading report: {str(e)}")
            return None
    
    def render_sidebar(self):
        """Render the sidebar with navigation and controls."""
        st.sidebar.title("🔍 Document Forensics")
        st.sidebar.markdown("---")
        
        # Authentication section
        st.sidebar.subheader("Authentication")
        if not st.session_state.auth_token:
            username = st.sidebar.text_input("Username")
            password = st.sidebar.text_input("Password", type="password")
            if st.sidebar.button("Login"):
                # Mock authentication for demo
                if username and password:
                    st.session_state.auth_token = "demo_token"
                    st.sidebar.success("Logged in successfully!")
                    st.rerun()
        else:
            st.sidebar.success("✅ Authenticated")
            if st.sidebar.button("Logout"):
                st.session_state.auth_token = None
                st.rerun()
        
        st.sidebar.markdown("---")
        
        # Navigation
        st.sidebar.subheader("Navigation")
        page = st.sidebar.radio(
            "Select Page",
            ["Upload & Analyze", "Document Library", "Batch Processing", "Reports"]
        )
        
        return page
    
    def render_upload_page(self):
        """Render the document upload and analysis page."""
        st.title("📤 Document Upload & Analysis")
        
        # File upload section
        st.subheader("Upload Document")
        uploaded_file = st.file_uploader(
            "Choose a document to analyze",
            type=['pdf', 'jpg', 'jpeg', 'png', 'tiff', 'docx', 'xlsx', 'txt'],
            help="Supported formats: PDF, Images (JPG, PNG, TIFF), Word documents, Excel files, Text files"
        )
        
        if uploaded_file is not None:
            # Display file information
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Filename", uploaded_file.name)
            with col2:
                st.metric("Size", f"{uploaded_file.size / 1024:.1f} KB")
            with col3:
                st.metric("Type", uploaded_file.type)
            
            # Upload metadata
            st.subheader("Upload Options")
            col1, col2 = st.columns(2)
            with col1:
                description = st.text_area("Description (optional)")
                tags = st.text_input("Tags (comma-separated)")
            with col2:
                priority = st.slider("Priority", 1, 10, 5)
                encrypt_file = st.checkbox("Encrypt stored file", value=True)
            
            # Upload button
            if st.button("Upload & Start Analysis", type="primary"):
                with st.spinner("Uploading document..."):
                    # Prepare metadata
                    metadata = {
                        "description": description if description else None,
                        "tags": [tag.strip() for tag in tags.split(",") if tag.strip()],
                        "priority": priority
                    }
                    
                    # Upload document
                    file_data = uploaded_file.read()
                    result = self.upload_document_to_api(file_data, uploaded_file.name, metadata)
                    
                    if result.get("success"):
                        st.success("✅ Document uploaded successfully!")
                        document_id = result.get("document_id")
                        
                        # Start analysis
                        if self.start_analysis(document_id):
                            st.success("🔬 Analysis started!")
                            st.session_state.current_document = document_id
                            st.rerun()
                        else:
                            st.error("Failed to start analysis")
                    else:
                        st.error(f"Upload failed: {result.get('error', 'Unknown error')}")
        
        # Current document analysis section
        if st.session_state.current_document:
            st.markdown("---")
            st.subheader("📊 Current Analysis")
            self.render_analysis_progress(st.session_state.current_document)
    
    def render_analysis_progress(self, document_id: int):
        """Render real-time analysis progress."""
        # Create placeholder for dynamic updates
        progress_placeholder = st.empty()
        results_placeholder = st.empty()
        
        # Progress tracking
        with progress_placeholder.container():
            status_info = self.get_document_status(document_id)
            
            if status_info:
                status = status_info.get("status", "unknown")
                current_step = status_info.get("current_step", "")
                
                if status == "processing":
                    st.info("🔄 Analysis in progress...")
                    progress_bar = st.progress(0.5)  # Indeterminate progress
                    
                    # Auto-refresh every 2 seconds
                    time.sleep(2)
                    st.rerun()
                    
                elif status == "completed":
                    # Check if this is a placeholder response
                    if "placeholder" in current_step.lower():
                        st.info("ℹ️ Analysis request received successfully!")
                        st.warning("⚠️ Full analysis execution requires database integration")
                        st.markdown("""
                        **Current Status**: Document uploaded and ready for analysis
                        
                        **What's Working**:
                        - ✅ Document upload
                        - ✅ File storage
                        - ✅ Analysis endpoint
                        
                        **What's Needed**:
                        - ⚠️ Database integration to map document UUID to file path
                        - ⚠️ Actual analysis execution
                        - ⚠️ Results storage and retrieval
                        
                        See documentation for implementation details.
                        """)
                    else:
                        st.success("✅ Analysis completed!")
                        
                        # Get and display results
                        results = self.get_analysis_results(document_id)
                        if results:
                            with results_placeholder.container():
                                self.render_analysis_results(results)
                    
                elif status == "failed":
                    st.error("❌ Analysis failed")
                    
                else:
                    st.warning(f"Status: {status}")
            else:
                st.warning("Unable to fetch document status")
    
    def render_analysis_results(self, results: Dict[str, Any]):
        """Render analysis results with visualizations."""
        st.subheader("🔍 Analysis Results")
        
        # Overall summary
        col1, col2, col3, col4 = st.columns(4)
        
        # Extract key metrics from results
        overall_risk = results.get("overall_risk_assessment", "unknown")
        confidence_score = results.get("confidence_score", 0.0)
        processing_time = results.get("processing_time", 0.0)
        
        with col1:
            risk_color = {
                "low": "green",
                "medium": "orange", 
                "high": "red",
                "critical": "red"
            }.get(overall_risk.lower(), "gray")
            st.metric("Overall Risk", overall_risk.upper(), delta_color=risk_color)
        
        with col2:
            st.metric("Confidence Score", f"{confidence_score:.2%}")
        
        with col3:
            st.metric("Processing Time", f"{processing_time:.1f}s")
        
        with col4:
            timestamp = results.get("timestamp", datetime.now().isoformat())
            st.metric("Analyzed", timestamp[:10])  # Show date only
        
        # Detailed results tabs
        tab1, tab2, tab3, tab4 = st.tabs(["📋 Summary", "🔍 Tampering", "✅ Authenticity", "📊 Visual Evidence"])
        
        with tab1:
            self.render_summary_tab(results)
        
        with tab2:
            self.render_tampering_tab(results)
        
        with tab3:
            self.render_authenticity_tab(results)
        
        with tab4:
            self.render_visual_evidence_tab(results)
        
        # Download report section
        st.markdown("---")
        st.subheader("📥 Download Report")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("Download PDF Report"):
                report_data = self.download_report(results.get("document_id"), "pdf")
                if report_data:
                    st.download_button(
                        "📄 Download PDF",
                        report_data,
                        file_name=f"forensics_report_{results.get('document_id')}.pdf",
                        mime="application/pdf"
                    )
        
        with col2:
            if st.button("Download JSON Report"):
                json_data = json.dumps(results, indent=2)
                st.download_button(
                    "📄 Download JSON",
                    json_data,
                    file_name=f"forensics_report_{results.get('document_id')}.json",
                    mime="application/json"
                )
        
        with col3:
            if st.button("Share Results"):
                st.info("🔗 Sharing functionality would be implemented here")
    
    def render_summary_tab(self, results: Dict[str, Any]):
        """Render summary tab with key findings."""
        st.write("### Key Findings")
        
        # Metadata analysis summary
        metadata_analysis = results.get("metadata_analysis")
        if metadata_analysis:
            st.write("#### 📄 Metadata Analysis")
            anomalies = metadata_analysis.get("anomalies", [])
            if anomalies:
                for anomaly in anomalies[:3]:  # Show top 3
                    st.warning(f"⚠️ {anomaly.get('description', 'Unknown anomaly')}")
            else:
                st.success("✅ No metadata anomalies detected")
        
        # Tampering analysis summary
        tampering_analysis = results.get("tampering_analysis")
        if tampering_analysis:
            st.write("#### 🔍 Tampering Detection")
            modifications = tampering_analysis.get("detected_modifications", [])
            if modifications:
                st.error(f"🚨 {len(modifications)} potential modifications detected")
                for mod in modifications[:3]:  # Show top 3
                    st.write(f"- {mod.get('description', 'Unknown modification')}")
            else:
                st.success("✅ No tampering detected")
        
        # Authenticity summary
        authenticity_analysis = results.get("authenticity_analysis")
        if authenticity_analysis:
            st.write("#### ✅ Authenticity Assessment")
            auth_score = authenticity_analysis.get("authenticity_score", {})
            overall_score = auth_score.get("overall_score", 0.0)
            
            if overall_score > 0.8:
                st.success(f"✅ High authenticity confidence ({overall_score:.1%})")
            elif overall_score > 0.6:
                st.warning(f"⚠️ Moderate authenticity confidence ({overall_score:.1%})")
            else:
                st.error(f"🚨 Low authenticity confidence ({overall_score:.1%})")
    
    def render_tampering_tab(self, results: Dict[str, Any]):
        """Render tampering analysis tab."""
        tampering_analysis = results.get("tampering_analysis")
        if not tampering_analysis:
            st.info("No tampering analysis results available")
            return
        
        st.write("### 🔍 Tampering Detection Results")
        
        # Overall risk assessment
        overall_risk = tampering_analysis.get("overall_risk", "unknown")
        confidence = tampering_analysis.get("confidence_score", 0.0)
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Risk Level", overall_risk.upper())
        with col2:
            st.metric("Detection Confidence", f"{confidence:.1%}")
        
        # Detected modifications
        modifications = tampering_analysis.get("detected_modifications", [])
        if modifications:
            st.write("#### Detected Modifications")
            for i, mod in enumerate(modifications):
                with st.expander(f"Modification {i+1}: {mod.get('type', 'Unknown')}"):
                    st.write(f"**Description:** {mod.get('description', 'No description')}")
                    st.write(f"**Confidence:** {mod.get('confidence', 0.0):.1%}")
                    st.write(f"**Location:** {mod.get('location', 'Unknown')}")
        
        # Pixel inconsistencies
        pixel_inconsistencies = tampering_analysis.get("pixel_inconsistencies", [])
        if pixel_inconsistencies:
            st.write("#### Pixel-Level Analysis")
            df_pixels = pd.DataFrame(pixel_inconsistencies)
            st.dataframe(df_pixels)
        
        # Text modifications
        text_modifications = tampering_analysis.get("text_modifications", [])
        if text_modifications:
            st.write("#### Text Modifications")
            for mod in text_modifications:
                st.write(f"- **Type:** {mod.get('modification_type', 'Unknown')}")
                st.write(f"  **Confidence:** {mod.get('confidence', 0.0):.1%}")
    
    def render_authenticity_tab(self, results: Dict[str, Any]):
        """Render authenticity analysis tab."""
        authenticity_analysis = results.get("authenticity_analysis")
        if not authenticity_analysis:
            st.info("No authenticity analysis results available")
            return
        
        st.write("### ✅ Authenticity Assessment")
        
        # Authenticity score breakdown
        auth_score = authenticity_analysis.get("authenticity_score", {})
        overall_score = auth_score.get("overall_score", 0.0)
        confidence_level = auth_score.get("confidence_level", 0.0)
        contributing_factors = auth_score.get("contributing_factors", {})
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Authenticity Score", f"{overall_score:.1%}")
        with col2:
            st.metric("Confidence Level", f"{confidence_level:.1%}")
        
        # Contributing factors
        if contributing_factors:
            st.write("#### Contributing Factors")
            MetricsDisplay.create_summary_chart(contributing_factors)
        
        # Structure validation
        structure_validation = authenticity_analysis.get("structure_validation")
        if structure_validation:
            st.write("#### File Structure Validation")
            is_valid = structure_validation.get("is_valid", False)
            compliance = structure_validation.get("format_compliance", 0.0)
            
            if is_valid:
                st.success(f"✅ Valid file structure (Compliance: {compliance:.1%})")
            else:
                st.error("❌ Invalid file structure detected")
                
            violations = structure_validation.get("violations", [])
            if violations:
                st.write("**Violations:**")
                for violation in violations:
                    st.write(f"- {violation}")
        
        # Comparison results
        comparison_results = authenticity_analysis.get("comparison_results", [])
        if comparison_results:
            st.write("#### Reference Comparisons")
            for comp in comparison_results:
                similarity = comp.get("similarity_score", 0.0)
                ref_id = comp.get("reference_id", "Unknown")
                st.write(f"**Reference {ref_id}:** {similarity:.1%} similarity")
    
    def render_visual_evidence_tab(self, results: Dict[str, Any]):
        """Render visual evidence tab."""
        visual_evidence = results.get("visual_evidence", [])
        if not visual_evidence:
            st.info("No visual evidence available")
            return
        
        st.write("### 📊 Visual Evidence")
        
        for i, evidence in enumerate(visual_evidence):
            VisualEvidenceRenderer.render_evidence_item(evidence, i)
    
    def render_document_library(self):
        """Render document library page."""
        st.title("📚 Document Library")
        
        # Mock document data for demonstration
        documents = [
            {"id": "doc1", "filename": "contract.pdf", "status": "completed", "risk": "low"},
            {"id": "doc2", "filename": "invoice.jpg", "status": "processing", "risk": "medium"},
            {"id": "doc3", "filename": "report.docx", "status": "completed", "risk": "high"},
        ]
        
        # Search and filter
        col1, col2, col3 = st.columns(3)
        with col1:
            search_term = st.text_input("🔍 Search documents")
        with col2:
            status_filter = st.selectbox("Status", ["All", "Pending", "Processing", "Completed", "Failed"])
        with col3:
            risk_filter = st.selectbox("Risk Level", ["All", "Low", "Medium", "High", "Critical"])
        
        # Document table
        if documents:
            df = pd.DataFrame(documents)
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No documents found")
    
    def render_batch_processing(self):
        """Render batch processing page."""
        st.title("📦 Batch Processing")
        
        # Batch upload
        st.subheader("Upload Multiple Documents")
        uploaded_files = st.file_uploader(
            "Choose documents to analyze",
            type=['pdf', 'jpg', 'jpeg', 'png', 'tiff', 'docx', 'xlsx', 'txt'],
            accept_multiple_files=True
        )
        
        if uploaded_files:
            st.write(f"Selected {len(uploaded_files)} files:")
            for file in uploaded_files:
                st.write(f"- {file.name} ({file.size / 1024:.1f} KB)")
            
            if st.button("Start Batch Analysis", type="primary"):
                st.success("Batch processing started!")
                # Batch processing logic would go here
        
        # Batch status
        st.subheader("Batch Status")
        st.info("Batch processing status would be displayed here")
    
    def render_reports(self):
        """Render reports page."""
        st.title("📊 Reports & Analytics")
        
        # Report generation
        st.subheader("Generate Reports")
        
        col1, col2 = st.columns(2)
        with col1:
            report_type = st.selectbox("Report Type", ["Summary", "Detailed", "Comparison"])
            date_range = st.date_input("Date Range", value=[])
        with col2:
            format_type = st.selectbox("Format", ["PDF", "JSON", "XML"])
            include_evidence = st.checkbox("Include Visual Evidence", value=True)
        
        if st.button("Generate Report"):
            st.success("Report generation started!")
        
        # Analytics dashboard
        st.subheader("Analytics Dashboard")
        
        # Mock analytics data
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Documents", "1,234", "12")
        with col2:
            st.metric("High Risk Documents", "45", "3")
        with col3:
            st.metric("Average Processing Time", "2.3s", "-0.1s")
        with col4:
            st.metric("Success Rate", "98.5%", "0.2%")
        
        # Charts
        st.subheader("Trends")
        
        # Mock chart data
        chart_data = pd.DataFrame({
            'Date': pd.date_range('2024-01-01', periods=30),
            'Documents Processed': range(30, 60),
            'High Risk Detected': [i % 7 for i in range(30)]
        })
        
        st.line_chart(chart_data.set_index('Date'))
    
    def run(self):
        """Run the Streamlit application."""
        # Render sidebar and get selected page
        page = self.render_sidebar()
        
        # Render selected page
        if page == "Upload & Analyze":
            self.render_upload_page()
        elif page == "Document Library":
            self.render_document_library()
        elif page == "Batch Processing":
            self.render_batch_processing()
        elif page == "Reports":
            self.render_reports()


def main():
    """Main entry point for the Streamlit app."""
    app = DocumentForensicsWebApp()
    app.run()


if __name__ == "__main__":
    main()