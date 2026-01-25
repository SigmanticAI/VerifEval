"""
Simulator selection logic
"""
import subprocess
from typing import Optional, List, Dict
from ..models import TBType, Simulator, Language


class SimulatorSelector:
    """Selects appropriate simulator based on TB type and availability"""
    
    def __init__(self):
        self._availability_cache: Dict[str, bool] = {}
    
    def select_simulator(
        self,
        tb_type: TBType,
        language: Language,
        preferred: Optional[str] = None
    ) -> Simulator:
        """
        Select simulator based on TB type, language, and availability
        
        Priority:
        1. Preferred simulator (if compatible and available)
        2. Default for TB type (if available)
        3. Fallback to available compatible simulator
        """
        # Try preferred simulator first
        if preferred:
            try:
                sim = Simulator(preferred.lower())
                if self._is_compatible(sim, tb_type, language) and self._is_available(sim):
                    return sim
            except ValueError:
                pass  # Invalid simulator name
        
        # Get default simulator for TB type
        default_sim = self._get_default_simulator(tb_type, language)
        if self._is_available(default_sim):
            return default_sim
        
        # Try fallbacks
        fallbacks = self._get_fallback_simulators(tb_type, language)
        for sim in fallbacks:
            if self._is_available(sim):
                return sim
        
        # UVM-SV special case
        if tb_type == TBType.UVM_SV:
            return Simulator.COMMERCIAL_REQUIRED
        
        # Last resort
        return default_sim
    
    def _get_default_simulator(self, tb_type: TBType, language: Language) -> Simulator:
        """Get default simulator for TB type and language"""
        
        # Python-based testbenches
        if tb_type in [TBType.COCOTB, TBType.PYUVM]:
            return Simulator.VERILATOR
        
        # VUnit (supports both Verilator and GHDL)
        if tb_type == TBType.VUNIT:
            if language == Language.VHDL:
                return Simulator.GHDL
            else:
                return Simulator.VERILATOR
        
        # VHDL testbenches
        if tb_type == TBType.VHDL or language == Language.VHDL:
            return Simulator.GHDL
        
        # SystemVerilog testbenches
        if tb_type == TBType.SYSTEMVERILOG or language == Language.SYSTEMVERILOG:
            return Simulator.VERILATOR
        
        # UVM-SV
        if tb_type == TBType.UVM_SV:
            return Simulator.COMMERCIAL_REQUIRED
        
        # Default
        return Simulator.VERILATOR
    
    def _get_fallback_simulators(self, tb_type: TBType, language: Language) -> List[Simulator]:
        """Get list of fallback simulators in priority order"""
        
        # Python testbenches can use either Verilator or Icarus
        if tb_type in [TBType.COCOTB, TBType.PYUVM]:
            return [Simulator.ICARUS, Simulator.VERILATOR]
        
        # VHDL must use GHDL (no fallback)
        if language == Language.VHDL:
            return [Simulator.GHDL]
        
        # SystemVerilog can use Verilator or Icarus
        if language == Language.SYSTEMVERILOG:
            return [Simulator.ICARUS, Simulator.VERILATOR]
        
        return [Simulator.VERILATOR, Simulator.ICARUS]
    
    def _is_compatible(self, sim: Simulator, tb_type: TBType, language: Language) -> bool:
        """Check if simulator is compatible with TB type and language"""
        
        # GHDL only supports VHDL
        if sim == Simulator.GHDL:
            return language == Language.VHDL or tb_type == TBType.VHDL
        
        # Verilator supports SystemVerilog/Verilog
        if sim == Simulator.VERILATOR:
            return language in [Language.SYSTEMVERILOG, Language.VERILOG, Language.PYTHON]
        
        # Icarus supports Verilog (limited SV support)
        if sim == Simulator.ICARUS:
            return language in [Language.VERILOG, Language.SYSTEMVERILOG, Language.PYTHON]
        
        return True
    
    def _is_available(self, sim: Simulator) -> bool:
        """Check if simulator is installed and available"""
        
        # Check cache first
        sim_name = sim.value
        if sim_name in self._availability_cache:
            return self._availability_cache[sim_name]
        
        # Special case
        if sim == Simulator.COMMERCIAL_REQUIRED:
            return False
        
        # Map simulator to command
        command_map = {
            Simulator.VERILATOR: 'verilator',
            Simulator.ICARUS: 'iverilog',
            Simulator.GHDL: 'ghdl'
        }
        
        cmd = command_map.get(sim)
        if not cmd:
            return False
        
        # Try to run --version
        try:
            result = subprocess.run(
                [cmd, '--version'],
                capture_output=True,
                timeout=5
            )
            available = result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            available = False
        
        # Cache result
        self._availability_cache[sim_name] = available
        return available
    
    def get_available_simulators(self) -> List[Simulator]:
        """Get list of all available simulators"""
        available = []
        for sim in [Simulator.VERILATOR, Simulator.ICARUS, Simulator.GHDL]:
            if self._is_available(sim):
                available.append(sim)
        return available
    
    def get_simulator_info(self, sim: Simulator) -> Dict[str, str]:
        """Get information about a simulator"""
        info = {
            Simulator.VERILATOR: {
                "name": "Verilator",
                "languages": "SystemVerilog, Verilog",
                "type": "Cycle-accurate",
                "speed": "Fast",
                "coverage": "Yes (with --coverage)",
                "install": "apt-get install verilator or build from source"
            },
            Simulator.ICARUS: {
                "name": "Icarus Verilog",
                "languages": "Verilog, limited SystemVerilog",
                "type": "Event-driven",
                "speed": "Medium",
                "coverage": "Limited",
                "install": "apt-get install iverilog"
            },
            Simulator.GHDL: {
                "name": "GHDL",
                "languages": "VHDL",
                "type": "Event-driven",
                "speed": "Medium",
                "coverage": "Yes (with --coverage)",
                "install": "apt-get install ghdl or build from source"
            },
            Simulator.COMMERCIAL_REQUIRED: {
                "name": "Commercial Simulator Required",
                "languages": "Full SystemVerilog/UVM",
                "type": "Event-driven",
                "speed": "Varies",
                "coverage": "Yes",
                "install": "Requires license (Xcelium, VCS, Questa)"
            }
        }
        
        return info.get(sim, {})
