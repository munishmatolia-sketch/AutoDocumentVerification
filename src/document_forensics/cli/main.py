"""Command-line interface for document forensics system."""

import asyncio
import json
import sys
import time
from pathlib import Path
from typing import Dict, Any, List, Optional
# UUID removed - using integer IDs

import click
import requests
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

from ..core.models import ProcessingStatus, RiskLevel
from ..core.config import settings


console = Console()


class DocumentForensicsCLI:
    """Command-line interface for document forensics operations."""
    
    def __init__(self, api_base_url: Optional[str] = None, auth_token: Optional[str] = None):
        """Initialize CLI with API configuration."""
        self.api_base_url = api_base_url or getattr(settings, 'API_BASE_URL', 'http://localhost:8000/api/v1')
        self.auth_token = auth_token
        self.session = requests.Session()
        
        if self.auth_token:
            self.session.headers.update({"Authorization": f"Bearer {self.auth_token}"})
    
    def upload_document(self, file_path: str, description: Optional[str] = None,
                       tags: Optional[List[str]] = None, priority: int = 5,
                       encrypt: bool = True) -> Dict[str, Any]:
        """Upload a document for analysis."""
        try:
            file_path = Path(file_path)
            if not file_path.exists():
                return {"success": False, "error": f"File not found: {file_path}"}
            
            with open(file_path, 'rb') as f:
                files = {"file": (file_path.name, f, "application/octet-stream")}
                
                metadata = {
                    "description": description,
                    "tags": tags or [],
                    "priority": priority
                }
                
                data = {"metadata": json.dumps(metadata)} if any(metadata.values()) else {}
                
                response = self.session.post(
                    f"{self.api_base_url}/documents/upload",
                    files=files,
                    data=data
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    return {"success": False, "error": f"Upload failed: {response.text}"}
                    
        except Exception as e:
            return {"success": False, "error": f"Upload error: {str(e)}"}
    
    def start_analysis(self, document_id: str) -> bool:
        """Start analysis for a document."""
        try:
            response = self.session.post(
                f"{self.api_base_url}/analysis/start",
                json={"document_id": document_id}
            )
            return response.status_code == 200
        except Exception:
            return False
    
    def get_document_status(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Get document processing status."""
        try:
            response = self.session.get(f"{self.api_base_url}/documents/{document_id}/status")
            if response.status_code == 200:
                return response.json()
            return None
        except Exception:
            return None
    
    def get_analysis_results(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Get analysis results for a document."""
        try:
            response = self.session.get(f"{self.api_base_url}/analysis/{document_id}")
            if response.status_code == 200:
                return response.json()
            return None
        except Exception:
            return None
    
    def upload_batch(self, file_paths: List[str], **kwargs) -> Dict[str, Any]:
        """Upload multiple documents as a batch."""
        try:
            files_data = []
            for file_path in file_paths:
                path = Path(file_path)
                if path.exists():
                    with open(path, 'rb') as f:
                        files_data.append({
                            "data": f.read(),
                            "filename": path.name,
                            "metadata": kwargs
                        })
            
            response = self.session.post(
                f"{self.api_base_url}/batch/upload",
                json={"files": files_data}
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return {"success": False, "error": f"Batch upload failed: {response.text}"}
                
        except Exception as e:
            return {"success": False, "error": f"Batch upload error: {str(e)}"}
    
    def get_batch_status(self, batch_id: str) -> Optional[Dict[str, Any]]:
        """Get batch processing status."""
        try:
            response = self.session.get(f"{self.api_base_url}/batch/{batch_id}/status")
            if response.status_code == 200:
                return response.json()
            return None
        except Exception:
            return None
    
    def download_report(self, document_id: str, output_path: str, format: str = "pdf") -> bool:
        """Download analysis report."""
        try:
            response = self.session.get(
                f"{self.api_base_url}/reports/{document_id}",
                params={"format": format}
            )
            
            if response.status_code == 200:
                with open(output_path, 'wb') as f:
                    f.write(response.content)
                return True
            return False
        except Exception:
            return False
    
    def wait_for_completion(self, document_id: str, timeout: int = 300) -> Optional[Dict[str, Any]]:
        """Wait for document analysis to complete."""
        start_time = time.time()
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TimeElapsedColumn(),
            console=console
        ) as progress:
            task = progress.add_task("Analyzing document...", total=None)
            
            while time.time() - start_time < timeout:
                status_info = self.get_document_status(document_id)
                
                if status_info:
                    status = status_info.get("status", "unknown")
                    
                    if status == "completed":
                        progress.update(task, description="✅ Analysis completed!")
                        return self.get_analysis_results(document_id)
                    elif status == "failed":
                        progress.update(task, description="❌ Analysis failed!")
                        return None
                    elif status == "processing":
                        progress.update(task, description="🔄 Processing...")
                
                time.sleep(2)
            
            progress.update(task, description="⏰ Timeout reached")
            return None


# CLI Commands
@click.group()
@click.option('--api-url', default=None, help='API base URL')
@click.option('--token', default=None, help='Authentication token')
@click.pass_context
def cli(ctx, api_url, token):
    """Document Forensics & Verification CLI."""
    ctx.ensure_object(dict)
    ctx.obj['cli'] = DocumentForensicsCLI(api_url, token)


@cli.command()
@click.argument('file_path', type=click.Path(exists=True))
@click.option('--description', '-d', help='Document description')
@click.option('--tags', '-t', multiple=True, help='Document tags')
@click.option('--priority', '-p', default=5, type=int, help='Processing priority (1-10)')
@click.option('--no-encrypt', is_flag=True, help='Disable encryption')
@click.option('--wait', '-w', is_flag=True, help='Wait for analysis completion')
@click.option('--output', '-o', help='Output file for report')
@click.option('--format', '-f', default='pdf', type=click.Choice(['pdf', 'json', 'xml']), help='Report format')
@click.pass_context
def analyze(ctx, file_path, description, tags, priority, no_encrypt, wait, output, format):
    """Analyze a single document."""
    cli_obj = ctx.obj['cli']
    
    console.print(f"📤 Uploading document: [bold]{file_path}[/bold]")
    
    # Upload document
    result = cli_obj.upload_document(
        file_path=file_path,
        description=description,
        tags=list(tags),
        priority=priority,
        encrypt=not no_encrypt
    )
    
    if not result.get("success"):
        console.print(f"❌ Upload failed: {result.get('error')}", style="red")
        sys.exit(1)
    
    document_id = result.get("document_id")
    console.print(f"✅ Document uploaded successfully! ID: [bold]{document_id}[/bold]")
    
    # Start analysis
    console.print("🔬 Starting analysis...")
    if not cli_obj.start_analysis(document_id):
        console.print("❌ Failed to start analysis", style="red")
        sys.exit(1)
    
    console.print("✅ Analysis started!")
    
    if wait:
        # Wait for completion
        results = cli_obj.wait_for_completion(document_id)
        
        if results:
            display_analysis_results(results)
            
            if output:
                console.print(f"📥 Downloading report to: [bold]{output}[/bold]")
                if cli_obj.download_report(document_id, output, format):
                    console.print("✅ Report downloaded successfully!")
                else:
                    console.print("❌ Failed to download report", style="red")
        else:
            console.print("❌ Analysis failed or timed out", style="red")
    else:
        console.print(f"🔍 Use 'forensics status {document_id}' to check progress")


@cli.command()
@click.argument('document_id')
@click.pass_context
def status(ctx, document_id):
    """Check document analysis status."""
    cli_obj = ctx.obj['cli']
    
    status_info = cli_obj.get_document_status(document_id)
    
    if not status_info:
        console.print(f"❌ Document not found: {document_id}", style="red")
        sys.exit(1)
    
    status = status_info.get("status", "unknown")
    
    # Create status display
    status_colors = {
        "pending": "yellow",
        "processing": "blue",
        "completed": "green",
        "failed": "red"
    }
    
    status_icons = {
        "pending": "⏳",
        "processing": "🔄",
        "completed": "✅",
        "failed": "❌"
    }
    
    color = status_colors.get(status, "white")
    icon = status_icons.get(status, "❓")
    
    console.print(Panel(
        f"{icon} Status: [bold {color}]{status.upper()}[/bold {color}]\n"
        f"Document ID: {document_id}",
        title="Document Status"
    ))
    
    if status == "completed":
        console.print("🔍 Use 'forensics results {document_id}' to view analysis results")


@cli.command()
@click.argument('document_id')
@click.option('--output', '-o', help='Output file for report')
@click.option('--format', '-f', default='json', type=click.Choice(['pdf', 'json', 'xml']), help='Output format')
@click.pass_context
def results(ctx, document_id, output, format):
    """Get analysis results for a document."""
    cli_obj = ctx.obj['cli']
    
    results = cli_obj.get_analysis_results(document_id)
    
    if not results:
        console.print(f"❌ No results found for document: {document_id}", style="red")
        sys.exit(1)
    
    if output:
        if format == 'json':
            with open(output, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            console.print(f"✅ Results saved to: [bold]{output}[/bold]")
        else:
            if cli_obj.download_report(document_id, output, format):
                console.print(f"✅ Report downloaded to: [bold]{output}[/bold]")
            else:
                console.print("❌ Failed to download report", style="red")
    else:
        display_analysis_results(results)


@cli.command()
@click.argument('directory', type=click.Path(exists=True, file_okay=False, dir_okay=True))
@click.option('--pattern', '-p', default='*', help='File pattern to match')
@click.option('--description', '-d', help='Batch description')
@click.option('--priority', default=5, type=int, help='Processing priority (1-10)')
@click.option('--wait', '-w', is_flag=True, help='Wait for batch completion')
@click.option('--max-files', default=100, type=int, help='Maximum number of files to process')
@click.pass_context
def batch(ctx, directory, pattern, description, priority, wait, max_files):
    """Process multiple documents in a directory."""
    cli_obj = ctx.obj['cli']
    
    # Find files matching pattern
    directory_path = Path(directory)
    files = list(directory_path.glob(pattern))[:max_files]
    
    if not files:
        console.print(f"❌ No files found matching pattern: {pattern}", style="red")
        sys.exit(1)
    
    console.print(f"📦 Found {len(files)} files to process")
    
    # Upload batch
    file_paths = [str(f) for f in files]
    result = cli_obj.upload_batch(
        file_paths=file_paths,
        description=description,
        priority=priority
    )
    
    if not result.get("success"):
        console.print(f"❌ Batch upload failed: {result.get('error')}", style="red")
        sys.exit(1)
    
    batch_id = result.get("batch_id")
    console.print(f"✅ Batch uploaded successfully! ID: [bold]{batch_id}[/bold]")
    
    if wait:
        # Monitor batch progress
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            console=console
        ) as progress:
            task = progress.add_task("Processing batch...", total=100)
            
            while True:
                batch_status = cli_obj.get_batch_status(batch_id)
                
                if batch_status:
                    progress_pct = batch_status.get("progress_percentage", 0)
                    status = batch_status.get("status", "unknown")
                    
                    progress.update(task, completed=progress_pct)
                    
                    if status == "completed":
                        progress.update(task, description="✅ Batch completed!")
                        break
                    elif status == "failed":
                        progress.update(task, description="❌ Batch failed!")
                        break
                
                time.sleep(3)
        
        # Display batch summary
        if batch_status:
            display_batch_summary(batch_status)
    else:
        console.print(f"🔍 Use 'forensics batch-status {batch_id}' to check progress")


@cli.command()
@click.argument('batch_id')
@click.pass_context
def batch_status(ctx, batch_id):
    """Check batch processing status."""
    cli_obj = ctx.obj['cli']
    
    batch_status = cli_obj.get_batch_status(batch_id)
    
    if not batch_status:
        console.print(f"❌ Batch not found: {batch_id}", style="red")
        sys.exit(1)
    
    display_batch_summary(batch_status)


@cli.command()
@click.argument('document_id')
@click.argument('output_path')
@click.option('--format', '-f', default='pdf', type=click.Choice(['pdf', 'json', 'xml']), help='Report format')
@click.pass_context
def download(ctx, document_id, output_path, format):
    """Download analysis report."""
    cli_obj = ctx.obj['cli']
    
    console.print(f"📥 Downloading {format.upper()} report...")
    
    if cli_obj.download_report(document_id, output_path, format):
        console.print(f"✅ Report downloaded to: [bold]{output_path}[/bold]")
    else:
        console.print("❌ Failed to download report", style="red")
        sys.exit(1)


def display_analysis_results(results: Dict[str, Any]):
    """Display analysis results in a formatted table."""
    console.print("\n" + "="*60)
    console.print("🔍 ANALYSIS RESULTS", style="bold blue", justify="center")
    console.print("="*60)
    
    # Overall summary
    overall_risk = results.get("overall_risk_assessment", "unknown")
    confidence_score = results.get("confidence_score", 0.0)
    processing_time = results.get("processing_time", 0.0)
    
    summary_table = Table(title="Summary")
    summary_table.add_column("Metric", style="cyan")
    summary_table.add_column("Value", style="magenta")
    
    # Risk level with color coding
    risk_colors = {"low": "green", "medium": "yellow", "high": "red", "critical": "red"}
    risk_color = risk_colors.get(overall_risk.lower(), "white")
    
    summary_table.add_row("Overall Risk", f"[{risk_color}]{overall_risk.upper()}[/{risk_color}]")
    summary_table.add_row("Confidence Score", f"{confidence_score:.1%}")
    summary_table.add_row("Processing Time", f"{processing_time:.2f}s")
    
    console.print(summary_table)
    
    # Tampering analysis
    tampering_analysis = results.get("tampering_analysis")
    if tampering_analysis:
        console.print("\n🔍 TAMPERING ANALYSIS", style="bold red")
        
        modifications = tampering_analysis.get("detected_modifications", [])
        if modifications:
            console.print(f"⚠️  {len(modifications)} potential modifications detected:")
            for i, mod in enumerate(modifications[:5], 1):  # Show top 5
                console.print(f"  {i}. {mod.get('description', 'Unknown modification')} "
                            f"(Confidence: {mod.get('confidence', 0.0):.1%})")
        else:
            console.print("✅ No tampering detected")
    
    # Authenticity analysis
    authenticity_analysis = results.get("authenticity_analysis")
    if authenticity_analysis:
        console.print("\n✅ AUTHENTICITY ANALYSIS", style="bold green")
        
        auth_score = authenticity_analysis.get("authenticity_score", {})
        overall_score = auth_score.get("overall_score", 0.0)
        
        if overall_score > 0.8:
            console.print(f"✅ High authenticity confidence ({overall_score:.1%})", style="green")
        elif overall_score > 0.6:
            console.print(f"⚠️  Moderate authenticity confidence ({overall_score:.1%})", style="yellow")
        else:
            console.print(f"🚨 Low authenticity confidence ({overall_score:.1%})", style="red")
    
    # Visual evidence
    visual_evidence = results.get("visual_evidence", [])
    if visual_evidence:
        console.print(f"\n📊 VISUAL EVIDENCE ({len(visual_evidence)} items)", style="bold blue")
        for i, evidence in enumerate(visual_evidence[:3], 1):  # Show top 3
            evidence_type = evidence.get("type", "unknown")
            description = evidence.get("description", "No description")
            console.print(f"  {i}. {evidence_type}: {description}")


def display_batch_summary(batch_status: Dict[str, Any]):
    """Display batch processing summary."""
    console.print("\n" + "="*50)
    console.print("📦 BATCH STATUS", style="bold blue", justify="center")
    console.print("="*50)
    
    batch_table = Table()
    batch_table.add_column("Metric", style="cyan")
    batch_table.add_column("Value", style="magenta")
    
    status = batch_status.get("status", "unknown")
    total_docs = batch_status.get("total_documents", 0)
    processed_docs = batch_status.get("processed_documents", 0)
    failed_docs = batch_status.get("failed_documents", 0)
    progress_pct = batch_status.get("progress_percentage", 0.0)
    
    # Status with color coding
    status_colors = {"pending": "yellow", "processing": "blue", "completed": "green", "failed": "red"}
    status_color = status_colors.get(status, "white")
    
    batch_table.add_row("Status", f"[{status_color}]{status.upper()}[/{status_color}]")
    batch_table.add_row("Progress", f"{progress_pct:.1f}%")
    batch_table.add_row("Total Documents", str(total_docs))
    batch_table.add_row("Processed", str(processed_docs))
    batch_table.add_row("Failed", str(failed_docs))
    batch_table.add_row("Success Rate", f"{((processed_docs - failed_docs) / max(processed_docs, 1)) * 100:.1f}%")
    
    console.print(batch_table)


if __name__ == '__main__':
    cli()