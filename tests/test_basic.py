"""
Basic Tests for VAL System
"""
import unittest
import sys
import os
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

class TestVALBasic(unittest.TestCase):
    """Basic functionality tests"""

    def test_imports(self):
        """Test that core modules can be imported"""
        try:
            from core.memory import memory
            from core.session import SESSION
            from engine.scaffold import apply_blueprint
            self.assertTrue(True)  # If we get here, imports work
        except ImportError as e:
            self.fail(f"Import failed: {e}")

    def test_memory_initialization(self):
        """Test memory system initializes"""
        from core.memory import memory
        self.assertIsNotNone(memory)
        self.assertTrue(hasattr(memory, 'conn'))

    def test_blueprint_validation(self):
        """Test blueprint validation"""
        from core.validator import validate_blueprint

        # Valid blueprint
        valid_bp = {
            "folders": ["src", "tests"],
            "files": [
                {"path": "README.md", "content": "# Test"}
            ]
        }
        result = validate_blueprint(valid_bp)
        self.assertIsInstance(result, dict)

        # Invalid blueprint
        invalid_bp = "not a dict"
        with self.assertRaises(ValueError):
            validate_blueprint(invalid_bp)

if __name__ == '__main__':
    unittest.main()