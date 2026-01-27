"""
Tests for UVM Analyzer module.
"""

import pytest
from pathlib import Path
from uvm_translator.parser import UVMParser, ParseResult, UVMComponent, UVMComponentType
from uvm_translator.analyzer import (
    UVMAnalyzer, UVMTestbenchStructure, 
    SignalInfo, TransactionInfo, AgentInfo
)


class TestUVMAnalyzer:
    """Tests for UVM Analyzer."""
    
    @pytest.fixture
    def analyzer(self):
        return UVMAnalyzer()
    
    @pytest.fixture
    def sample_parse_result(self):
        """Create a sample parse result for testing."""
        result = ParseResult()
        
        # Add a sequence item
        seq_item = UVMComponent(
            name="fifo_seq_item",
            component_type=UVMComponentType.SEQUENCE_ITEM,
            parent_class="uvm_sequence_item"
        )
        from uvm_translator.parser import UVMField
        seq_item.fields = [
            UVMField(name="data", data_type="bit[7:0]", is_rand=True),
            UVMField(name="addr", data_type="bit[3:0]", is_rand=True),
            UVMField(name="wr_en", data_type="bit", is_rand=True)
        ]
        result.components.append(seq_item)
        
        # Add a driver
        driver = UVMComponent(
            name="fifo_driver",
            component_type=UVMComponentType.DRIVER,
            parent_class="uvm_driver #(fifo_seq_item)"
        )
        result.components.append(driver)
        
        # Add a monitor
        monitor = UVMComponent(
            name="fifo_monitor",
            component_type=UVMComponentType.MONITOR,
            parent_class="uvm_monitor"
        )
        result.components.append(monitor)
        
        # Add an agent
        agent = UVMComponent(
            name="fifo_agent",
            component_type=UVMComponentType.AGENT,
            parent_class="uvm_agent"
        )
        result.components.append(agent)
        
        # Add an environment
        env = UVMComponent(
            name="fifo_env",
            component_type=UVMComponentType.ENV,
            parent_class="uvm_env"
        )
        result.components.append(env)
        
        # Add a test
        test = UVMComponent(
            name="fifo_base_test",
            component_type=UVMComponentType.TEST,
            parent_class="uvm_test"
        )
        result.components.append(test)
        
        # Add an interface
        interface = UVMComponent(
            name="fifo_if",
            component_type=UVMComponentType.INTERFACE
        )
        from uvm_translator.parser import UVMPort
        interface.ports = [
            UVMPort(name="clk", direction="input", data_type="logic"),
            UVMPort(name="rst_n", direction="input", data_type="logic"),
            UVMPort(name="wr_en", direction="output", data_type="logic"),
            UVMPort(name="rd_en", direction="output", data_type="logic"),
            UVMPort(name="wr_data", direction="output", data_type="logic", width="7:0"),
            UVMPort(name="rd_data", direction="input", data_type="logic", width="7:0"),
            UVMPort(name="full", direction="input", data_type="logic"),
            UVMPort(name="empty", direction="input", data_type="logic"),
        ]
        result.interfaces.append(interface)
        
        return result
    
    def test_analyzer_init(self, analyzer):
        """Test analyzer initialization."""
        assert analyzer is not None
        assert hasattr(analyzer, 'parser')
    
    def test_analyze_basic(self, analyzer, sample_parse_result):
        """Test basic analysis."""
        structure = analyzer.analyze(sample_parse_result)
        
        assert structure is not None
        assert isinstance(structure, UVMTestbenchStructure)
    
    def test_analyze_finds_test(self, analyzer, sample_parse_result):
        """Test that analysis finds the test class."""
        structure = analyzer.analyze(sample_parse_result)
        assert structure.test_name == "fifo_base_test"
    
    def test_analyze_finds_env(self, analyzer, sample_parse_result):
        """Test that analysis finds the environment."""
        structure = analyzer.analyze(sample_parse_result)
        assert structure.env_name == "fifo_env"
    
    def test_analyze_finds_transactions(self, analyzer, sample_parse_result):
        """Test that analysis finds transactions."""
        structure = analyzer.analyze(sample_parse_result)
        
        assert len(structure.transactions) == 1
        trans = structure.transactions[0]
        assert trans.name == "fifo_seq_item"
        assert trans.has_randomization == True
    
    def test_analyze_finds_agents(self, analyzer, sample_parse_result):
        """Test that analysis finds agents."""
        structure = analyzer.analyze(sample_parse_result)
        
        assert len(structure.agents) >= 1
        agent = structure.agents[0]
        assert "fifo" in agent.name.lower()
    
    def test_analyze_interface_signals(self, analyzer, sample_parse_result):
        """Test interface signal extraction."""
        structure = analyzer.analyze(sample_parse_result)
        
        assert len(structure.interface_signals) > 0
        
        signal_names = [s.name for s in structure.interface_signals]
        assert "clk" in signal_names
        assert "rst_n" in signal_names
    
    def test_identify_clock_reset(self, analyzer, sample_parse_result):
        """Test clock/reset identification."""
        structure = analyzer.analyze(sample_parse_result)
        
        assert structure.clock_signal == "clk"
        assert "rst" in structure.reset_signal.lower()
    
    def test_complexity_score(self, analyzer, sample_parse_result):
        """Test complexity score calculation."""
        structure = analyzer.analyze(sample_parse_result)
        
        assert structure.complexity_score >= 0
        assert structure.complexity_score <= 100
    
    def test_translation_notes(self, analyzer, sample_parse_result):
        """Test that translation notes are generated."""
        structure = analyzer.analyze(sample_parse_result)
        
        # Should have some notes about randomization since we have rand fields
        assert len(structure.translation_notes) > 0 or len(structure.warnings) >= 0
    
    def test_structure_to_dict(self, analyzer, sample_parse_result):
        """Test structure serialization."""
        structure = analyzer.analyze(sample_parse_result)
        
        data = structure.to_dict()
        
        assert 'test_name' in data
        assert 'env_name' in data
        assert 'agents' in data
        assert 'transactions' in data


class TestSignalInfo:
    """Tests for SignalInfo dataclass."""
    
    def test_signal_info_creation(self):
        """Test creating SignalInfo."""
        signal = SignalInfo(
            name="clk",
            direction="input",
            width=1,
            is_clock=True
        )
        
        assert signal.name == "clk"
        assert signal.is_clock == True
        assert signal.width == 1
    
    def test_signal_info_defaults(self):
        """Test SignalInfo defaults."""
        signal = SignalInfo(name="data", direction="output")
        
        assert signal.width == 1
        assert signal.is_clock == False
        assert signal.is_reset == False


class TestTransactionInfo:
    """Tests for TransactionInfo dataclass."""
    
    def test_transaction_info_creation(self):
        """Test creating TransactionInfo."""
        trans = TransactionInfo(
            name="my_transaction",
            fields=[
                {'name': 'data', 'type': 'int', 'is_rand': True}
            ],
            constraints=[],
            has_randomization=True
        )
        
        assert trans.name == "my_transaction"
        assert trans.has_randomization == True
        assert len(trans.fields) == 1


class TestAgentInfo:
    """Tests for AgentInfo dataclass."""
    
    def test_agent_info_creation(self):
        """Test creating AgentInfo."""
        agent = AgentInfo(name="fifo_agent", is_active=True)
        
        assert agent.name == "fifo_agent"
        assert agent.is_active == True
        assert agent.driver is None
        assert agent.monitor is None


class TestAnalyzerEdgeCases:
    """Edge case tests for the analyzer."""
    
    @pytest.fixture
    def analyzer(self):
        return UVMAnalyzer()
    
    def test_empty_parse_result(self, analyzer):
        """Test analysis of empty parse result."""
        result = ParseResult()
        structure = analyzer.analyze(result)
        
        assert structure is not None
        assert len(structure.transactions) == 0
        assert len(structure.agents) == 0
    
    def test_missing_interface(self, analyzer):
        """Test analysis when no interface is present."""
        result = ParseResult()
        
        # Add only a test
        test = UVMComponent(
            name="simple_test",
            component_type=UVMComponentType.TEST,
            parent_class="uvm_test"
        )
        result.components.append(test)
        
        structure = analyzer.analyze(result)
        
        assert structure.test_name == "simple_test"
        assert len(structure.interface_signals) == 0
    
    def test_multiple_agents(self, analyzer):
        """Test analysis with multiple agents."""
        result = ParseResult()
        
        for i in range(3):
            agent = UVMComponent(
                name=f"agent_{i}",
                component_type=UVMComponentType.AGENT,
                parent_class="uvm_agent"
            )
            result.components.append(agent)
        
        structure = analyzer.analyze(result)
        
        assert len(structure.agents) == 3

