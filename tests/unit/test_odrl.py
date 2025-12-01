"""Unit tests for ODRL policy evaluator."""
import pytest

from src.utils.odrl import ODRLEvaluator, EvaluationResult


class TestODRLEvaluator:
    """Tests for ODRL policy evaluator."""
    
    def test_evaluator_initialization(self):
        """Test evaluator initialization."""
        evaluator = ODRLEvaluator()
        assert evaluator is not None
    
    def test_evaluate_no_policy(self):
        """Test evaluation with no policy grants access."""
        evaluator = ODRLEvaluator()
        result = evaluator.evaluate(None, {}, "use")
        
        assert result.allowed is True
        assert "No policy defined" in result.reason
    
    def test_evaluate_empty_policy(self):
        """Test evaluation with empty policy grants access."""
        evaluator = ODRLEvaluator()
        result = evaluator.evaluate({}, {}, "use")
        
        assert result.allowed is True
    
    def test_evaluate_simple_permission(self):
        """Test evaluation with simple permission."""
        evaluator = ODRLEvaluator()
        
        policy = {
            "permission": [
                {
                    "action": "use",
                    "target": "urn:data:test"
                }
            ]
        }
        
        result = evaluator.evaluate(policy, {}, "use")
        
        assert result.allowed is True
        assert result.reason == "Permission granted"
    
    def test_evaluate_action_mismatch(self):
        """Test evaluation fails when action doesn't match."""
        evaluator = ODRLEvaluator()
        
        policy = {
            "permission": [
                {
                    "action": "read",
                    "target": "urn:data:test"
                }
            ]
        }
        
        result = evaluator.evaluate(policy, {}, "use")
        
        assert result.allowed is False
    
    def test_evaluate_with_constraint_satisfied(self):
        """Test evaluation with satisfied constraint."""
        evaluator = ODRLEvaluator()
        
        policy = {
            "permission": [
                {
                    "action": "use",
                    "target": "urn:data:test",
                    "constraint": [
                        {
                            "leftOperand": "purpose",
                            "operator": "eq",
                            "rightOperand": "research"
                        }
                    ]
                }
            ]
        }
        
        context = {"purpose": "research"}
        result = evaluator.evaluate(policy, context, "use")
        
        assert result.allowed is True
    
    def test_evaluate_with_constraint_not_satisfied(self):
        """Test evaluation with unsatisfied constraint."""
        evaluator = ODRLEvaluator()
        
        policy = {
            "permission": [
                {
                    "action": "use",
                    "target": "urn:data:test",
                    "constraint": [
                        {
                            "leftOperand": "purpose",
                            "operator": "eq",
                            "rightOperand": "research"
                        }
                    ]
                }
            ]
        }
        
        context = {"purpose": "commercial"}
        result = evaluator.evaluate(policy, context, "use")
        
        assert result.allowed is False
    
    def test_evaluate_with_missing_context(self):
        """Test evaluation with missing context value."""
        evaluator = ODRLEvaluator()
        
        policy = {
            "permission": [
                {
                    "action": "use",
                    "target": "urn:data:test",
                    "constraint": [
                        {
                            "leftOperand": "purpose",
                            "operator": "eq",
                            "rightOperand": "research"
                        }
                    ]
                }
            ]
        }
        
        context = {}  # Missing purpose
        result = evaluator.evaluate(policy, context, "use")
        
        assert result.allowed is False
    
    def test_evaluate_prohibition(self):
        """Test evaluation with prohibition."""
        evaluator = ODRLEvaluator()
        
        policy = {
            "prohibition": [
                {
                    "action": "distribute",
                    "target": "urn:data:test"
                }
            ],
            "permission": [
                {
                    "action": "distribute",
                    "target": "urn:data:test"
                }
            ]
        }
        
        result = evaluator.evaluate(policy, {}, "distribute")
        
        assert result.allowed is False
        assert "prohibited" in result.reason.lower()
    
    def test_evaluate_multiple_actions(self):
        """Test evaluation with multiple allowed actions."""
        evaluator = ODRLEvaluator()
        
        policy = {
            "permission": [
                {
                    "action": ["use", "read", "distribute"],
                    "target": "urn:data:test"
                }
            ]
        }
        
        assert evaluator.evaluate(policy, {}, "use").allowed is True
        assert evaluator.evaluate(policy, {}, "read").allowed is True
        assert evaluator.evaluate(policy, {}, "distribute").allowed is True
        assert evaluator.evaluate(policy, {}, "modify").allowed is False
    
    def test_compare_operators(self):
        """Test various comparison operators."""
        evaluator = ODRLEvaluator()
        
        # Test eq
        assert evaluator._compare("test", "eq", "test") is True
        assert evaluator._compare("test", "eq", "other") is False
        
        # Test neq
        assert evaluator._compare("test", "neq", "other") is True
        assert evaluator._compare("test", "neq", "test") is False
        
        # Test gt
        assert evaluator._compare(10, "gt", 5) is True
        assert evaluator._compare(5, "gt", 10) is False
        
        # Test gteq
        assert evaluator._compare(10, "gteq", 10) is True
        assert evaluator._compare(10, "gteq", 5) is True
        
        # Test lt
        assert evaluator._compare(5, "lt", 10) is True
        assert evaluator._compare(10, "lt", 5) is False
        
        # Test lteq
        assert evaluator._compare(10, "lteq", 10) is True
        assert evaluator._compare(5, "lteq", 10) is True
        
        # Test isAnyOf
        assert evaluator._compare("a", "isAnyOf", ["a", "b", "c"]) is True
        assert evaluator._compare("d", "isAnyOf", ["a", "b", "c"]) is False
        
        # Test isNoneOf
        assert evaluator._compare("d", "isNoneOf", ["a", "b", "c"]) is True
        assert evaluator._compare("a", "isNoneOf", ["a", "b", "c"]) is False
    
    def test_create_default_policy(self):
        """Test creating default policy."""
        evaluator = ODRLEvaluator()
        
        policy = evaluator.create_default_policy(
            target="urn:data:test-dataset",
            allowed_actions=["use", "read"],
            purpose="research"
        )
        
        assert "@context" in policy
        assert policy["@type"] == "Policy"
        assert "permission" in policy
        assert len(policy["permission"]) == 1
        
        permission = policy["permission"][0]
        assert permission["target"] == "urn:data:test-dataset"
        assert "use" in permission["action"]
        assert "read" in permission["action"]
        assert len(permission["constraint"]) == 1
    
    def test_evaluation_result(self):
        """Test EvaluationResult model."""
        result = EvaluationResult(
            allowed=True,
            reason="Test reason",
            duties=[{"action": "log"}]
        )
        
        assert result.allowed is True
        assert result.reason == "Test reason"
        assert len(result.duties) == 1
        
        result_dict = result.to_dict()
        assert result_dict["allowed"] is True
        assert result_dict["reason"] == "Test reason"
        assert result_dict["duties"] == [{"action": "log"}]
