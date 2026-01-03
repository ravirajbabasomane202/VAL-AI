"""
Project Health Scanner - IDE-like Diagnostics
"""
from pathlib import Path
from typing import Dict, List
from core.memory import memory
from core.session import SESSION
from engine.env_manager import detect_project_type
from engine.dep_intelligence import check_outdated

class HealthScanner:
    """Scan project for health issues and missing components"""
    
    def __init__(self, project_path: Path = None):
        if project_path is None:
            try:
                from core.session import SESSION
                project_path = Path(SESSION.get("last_project", {}).get("path", "."))
            except:
                project_path = Path(".")
        self.project_path = project_path
    
    def scan_health(self) -> Dict:
        """Comprehensive health scan"""
        report = {
            "score": 0,
            "issues": [],
            "warnings": [],
            "good": [],
            "production_ready": True
        }
        
        # Check for essential files
        essentials = {
            "README.md": "Documentation",
            ".gitignore": "Version control ignores",
            "LICENSE": "Legal license",
            "requirements.txt": "Python dependencies",
            "package.json": "Node.js dependencies",
            "Dockerfile": "Containerization",
            "docker-compose.yml": "Multi-container setup",
            ".env.example": "Environment template"
        }
        
        for file, desc in essentials.items():
            if (self.project_path / file).exists():
                report["good"].append(f"✅ {desc} present")
                report["score"] += 10
            else:
                report["issues"].append(f"❌ Missing {desc} ({file})")
                if file in ["README.md", ".gitignore"]:
                    report["production_ready"] = False
        
        # Check for test directory
        test_dirs = ["tests", "test", "__tests__", "spec"]
        has_tests = any((self.project_path / d).exists() for d in test_dirs)
        if has_tests:
            report["good"].append("✅ Test directory present")
            report["score"] += 15
        else:
            report["issues"].append("❌ No test directory found")
            report["production_ready"] = False
        
        # Check for CI/CD
        ci_files = [".github/workflows", ".gitlab-ci.yml", "Jenkinsfile", ".travis.yml"]
        has_ci = any((self.project_path / f).exists() for f in ci_files)
        if has_ci:
            report["good"].append("✅ CI/CD configuration present")
            report["score"] += 10
        else:
            report["warnings"].append("⚠️ No CI/CD configuration")
        
        # Check code quality
        ptype = detect_project_type(self.project_path)
        if ptype == "python":
            if (self.project_path / "setup.py").exists() or (self.project_path / "pyproject.toml").exists():
                report["good"].append("✅ Python packaging configured")
                report["score"] += 5
            else:
                report["warnings"].append("⚠️ No Python packaging (setup.py/pyproject.toml)")
        
        # Check for security
        if (self.project_path / ".env").exists():
            report["good"].append("✅ Environment variables configured")
            report["score"] += 5
        else:
            report["warnings"].append("⚠️ No .env file (environment variables)")
        
        # Check dependencies
        try:
            outdated = check_outdated(self.project_path)
            if "Outdated" in outdated:
                report["warnings"].append("⚠️ Outdated dependencies detected")
            else:
                report["good"].append("✅ Dependencies up to date")
                report["score"] += 5
        except:
            report["warnings"].append("⚠️ Could not check dependency status")
        
        # Check for documentation
        doc_files = ["docs", "doc", "README.md", "CHANGELOG.md", "CONTRIBUTING.md"]
        has_docs = any((self.project_path / f).exists() for f in doc_files)
        if has_docs:
            report["good"].append("✅ Documentation present")
            report["score"] += 10
        else:
            report["warnings"].append("⚠️ Limited documentation")
        
        # Calculate final score
        max_score = 60  # Based on checks above
        report["score"] = min(100, int((report["score"] / max_score) * 100))
        
        # Production readiness
        if report["score"] < 70:
            report["production_ready"] = False
        
        return report
    
    def format_report(self, report: Dict) -> str:
        """Format health report for display"""
        output = f"🏥 Project Health Report (Score: {report['score']}/100)\n\n"
        
        if report["issues"]:
            output += "🚨 Critical Issues:\n" + "\n".join(report["issues"]) + "\n\n"
        
        if report["warnings"]:
            output += "⚠️ Warnings:\n" + "\n".join(report["warnings"]) + "\n\n"
        
        if report["good"]:
            output += "✅ Good Practices:\n" + "\n".join(report["good"]) + "\n\n"
        
        readiness = "✅ Production Ready" if report["production_ready"] else "❌ Not Production Ready"
        output += f"📊 Overall: {readiness}\n"
        
        return output
    
    def quick_check(self) -> str:
        """Quick health summary"""
        report = self.scan_health()
        
        if report["issues"]:
            return f"🚨 Health: {len(report['issues'])} issues, {len(report['warnings'])} warnings (Score: {report['score']})"
        elif report["warnings"]:
            return f"⚠️ Health: {len(report['warnings'])} warnings (Score: {report['score']})"
        else:
            return f"✅ Health: All good (Score: {report['score']})"

# Global scanner instance
scanner = HealthScanner()