import asyncio
import sys
import os

# Fix for Windows path issues
import os
import sys

# Ensure the BACKEND directory is in sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app.services.risk_engine import calculate_risk_enhanced

async def test_risk_logic():
    print("Testing Dual-Engine Risk Analysis (v8)...")
    
    # Mock some clauses
    mock_clauses = [
        {"type": "Termination", "text": "This agreement may be terminated by either party without cause upon 2 days notice.", "page_number": 1},
        {"type": "Indemnity", "text": "Party A shall indemnify Party B for all losses whatsoever without limit.", "page_number": 2},
        {"type": "Payment", "text": "Payments are due net 90 days from arrival.", "page_number": 3}
    ]
    
    # Note: Mandatory clauses missing: Confidentiality, Liability, Governing Law
    
    try:
        results = await calculate_risk_enhanced(mock_clauses, "This is a Service Agreement preview.")
        print("\n--- RESULTS ---")
        print(f"Contract Type: {results['contract_type']}")
        print(f"Overall Score: {results['score']}%")
        print(f"Risk Level: {results['level']}")
        print(f"Breakdown: {results['breakdown']}")
        
        print("\n--- DETECTED RISKS ---")
        for i, r in enumerate(results['risks'], 1):
            print(f"{i}. [{r['severity']}] {r['title']}")
            print(f"   Method: {r['detection_method']}")
            print(f"   Reason: {r['reason']}")
            print(f"   Source: {r['source']}")
            print("-" * 30)
            
    except Exception as e:
        print(f"Test failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_risk_logic())
