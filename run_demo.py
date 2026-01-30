#!/usr/bin/env python3
"""
Simple demo script to test the document forensics system locally.
"""

import os
import sys
import subprocess
from pathlib import Path

def check_python_version():
    """Check if Python version is compatible."""
    if sys.version_info < (3, 9):
        print("❌ Python 3.9+ is required")
        return False
    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor} detected")
    return True

def install_dependencies():
    """Install required dependencies."""
    print("📦 Installing dependencies...")
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], 
                      check=True, capture_output=True)
        print("✅ Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install dependencies: {e}")
        return False

def setup_environment():
    """Set up environment variables."""
    print("🔧 Setting up environment...")
    
    # Create necessary directories
    os.makedirs("uploads", exist_ok=True)
    os.makedirs("logs", exist_ok=True)
    os.makedirs("models", exist_ok=True)
    
    # Set environment variables
    os.environ["PYTHONPATH"] = str(Path("src").absolute())
    os.environ["DATABASE_URL"] = "sqlite:///./document_forensics.db"
    os.environ["REDIS_URL"] = "redis://localhost:6379/0"
    
    print("✅ Environment configured")
    return True

def run_simple_test():
    """Run a simple test of the document forensics system."""
    print("🧪 Running simple test...")
    
    try:
        # Import the main modules
        sys.path.insert(0, "src")
        from document_forensics.analysis.metadata_extractor import MetadataExtractor
        from document_forensics.analysis.authenticity_scorer import AuthenticityScorer
        from document_forensics.analysis.tampering_detector import TamperingDetector
        
        print("✅ Core modules imported successfully")
        
        # Test with demo documents if they exist
        demo_files = [
            "demo_documents/original_contract.txt",
            "demo_data/original_documents/legal_contract_original.txt"
        ]
        
        for demo_file in demo_files:
            if os.path.exists(demo_file):
                print(f"📄 Testing with {demo_file}")
                
                # Test metadata extraction
                extractor = MetadataExtractor()
                metadata = extractor.extract_metadata(demo_file)
                print(f"   📊 Metadata extracted: {len(metadata.dict())} fields")
                
                # Test authenticity scoring
                scorer = AuthenticityScorer()
                auth_result = scorer.calculate_authenticity_score(demo_file)
                print(f"   🔍 Authenticity score: {auth_result.authenticity_score:.2f}")
                
                # Test tampering detection
                detector = TamperingDetector()
                tamper_result = detector.detect_tampering(demo_file)
                print(f"   🚨 Tampering detected: {tamper_result.tampering_detected}")
                
                break
        else:
            print("⚠️  No demo files found, but modules loaded successfully")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

def run_streamlit_app():
    """Run the Streamlit web interface."""
    print("🌐 Starting Streamlit web interface...")
    print("   📍 Open http://localhost:8501 in your browser")
    print("   🛑 Press Ctrl+C to stop")
    
    try:
        subprocess.run([
            sys.executable, "-m", "streamlit", "run", 
            "src/document_forensics/web/streamlit_app.py",
            "--server.port=8501"
        ])
    except KeyboardInterrupt:
        print("\n👋 Streamlit app stopped")

def main():
    """Main demo function."""
    print("🔬 Document Forensics System Demo")
    print("=" * 40)
    
    # Check prerequisites
    if not check_python_version():
        return 1
    
    # Install dependencies
    if not install_dependencies():
        print("💡 Try running: pip install -r requirements.txt")
        return 1
    
    # Setup environment
    if not setup_environment():
        return 1
    
    # Run tests
    if not run_simple_test():
        print("⚠️  Some tests failed, but continuing...")
    
    # Ask user what to do next
    print("\n🎯 What would you like to do?")
    print("1. Run Streamlit web interface")
    print("2. Exit")
    
    choice = input("Enter your choice (1-2): ").strip()
    
    if choice == "1":
        run_streamlit_app()
    else:
        print("👋 Demo completed!")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())