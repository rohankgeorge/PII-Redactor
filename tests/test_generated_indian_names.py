import subprocess
import sys
from pathlib import Path
import unittest


class TestGeneratedIndianNames(unittest.TestCase):
    def test_generated_module_is_up_to_date(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        script = repo_root / "scripts" / "build_indian_name_lists.py"
        result = subprocess.run(
            [sys.executable, str(script), "--check"],
            capture_output=True,
            text=True,
            check=False,
        )
        message = (result.stdout + "\n" + result.stderr).strip()
        self.assertEqual(result.returncode, 0, message)


if __name__ == "__main__":
    unittest.main()
