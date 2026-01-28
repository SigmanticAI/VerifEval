### `step2_classify_route/detectors/README.md`

```markdown
# Detectors Module

## Purpose

Detects testbench type by analyzing file contents for framework-specific
patterns (imports, decorators, class hierarchies).

## Detection Priority

Detectors are run in this order (most specific first):
1. **PyUVMDetector** - Python UVM implementation
2. **CocoTBDetector** - Python cocotb framework
3. **UVMSVDetector** - SystemVerilog UVM (flags commercial requirement)
4. **VUnitDetector** - VUnit test framework
5. **HDLDetector** - Generic SV/VHDL (fallback)

## Adding a New Detector

```python
from .base import BaseDetector
from ..models import DetectionResult, TBType, Language

class MyFrameworkDetector(BaseDetector):
    def __init__(self):
        super().__init__()
        self.tb_type = TBType.MY_FRAMEWORK
        self.language = Language.PYTHON  # or SYSTEMVERILOG, VHDL
        self.file_extensions = ['.py']
        self.detection_patterns = [
            r'import\s+my_framework',
            r'@my_framework\.test',
        ]
    
    def detect(self, file_path: Path) -> Optional[DetectionResult]:
        if file_path.suffix not in self.file_extensions:
            return None
        
        content = self.read_file_safe(file_path)
        if not content:
            return None
        
        if self.matches_patterns(content, self.detection_patterns):
            return DetectionResult(
                tb_type=self.tb_type,
                confidence=0.90,
                files_detected=[str(file_path)],
                detection_method="pattern_matching",
                language=self.language
            )
        return None
