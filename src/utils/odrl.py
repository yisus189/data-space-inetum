"""ODRL Policy Evaluator for usage policy enforcement."""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class ODRLAction(str, Enum):
    """ODRL action types."""
    USE = "use"
    READ = "read"
    DISTRIBUTE = "distribute"
    MODIFY = "modify"
    DELETE = "delete"
    TRANSFER = "transfer"


class ODRLOperator(str, Enum):
    """ODRL constraint operators."""
    EQ = "eq"
    NEQ = "neq"
    GT = "gt"
    GTE = "gteq"
    LT = "lt"
    LTE = "lteq"
    IS_A = "isA"
    IS_NONE_OF = "isNoneOf"
    IS_ALL_OF = "isAllOf"
    IS_ANY_OF = "isAnyOf"


class EvaluationResult:
    """Result of policy evaluation."""
    
    def __init__(
        self,
        allowed: bool,
        reason: Optional[str] = None,
        duties: Optional[List[Dict]] = None
    ):
        self.allowed = allowed
        self.reason = reason
        self.duties = duties or []
    
    def to_dict(self) -> Dict:
        return {
            "allowed": self.allowed,
            "reason": self.reason,
            "duties": self.duties
        }


class ODRLEvaluator:
    """
    Simple ODRL policy evaluator.
    
    Evaluates ODRL policies to determine if an action is allowed.
    This is a simplified implementation focused on common use cases.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def evaluate(
        self,
        policy: Dict[str, Any],
        context: Dict[str, Any],
        action: str = "use"
    ) -> EvaluationResult:
        """
        Evaluate if an action is allowed based on policy and context.
        
        Args:
            policy: ODRL policy JSON
            context: Context containing actor info, timestamp, purpose, etc.
            action: The action being requested
        
        Returns:
            EvaluationResult with allowed status and reason
        """
        if not policy:
            return EvaluationResult(
                allowed=True,
                reason="No policy defined, access granted by default"
            )
        
        # Check prohibitions first
        prohibitions = policy.get("prohibition", [])
        for prohibition in prohibitions:
            if self._matches_rule(prohibition, action, context):
                return EvaluationResult(
                    allowed=False,
                    reason=f"Action '{action}' is prohibited by policy"
                )
        
        # Check permissions
        permissions = policy.get("permission", [])
        for permission in permissions:
            result = self._evaluate_permission(permission, action, context)
            if result.allowed:
                return result
        
        # No matching permission found
        return EvaluationResult(
            allowed=False,
            reason=f"No permission grants action '{action}'"
        )
    
    def _matches_rule(
        self,
        rule: Dict[str, Any],
        action: str,
        context: Dict[str, Any]
    ) -> bool:
        """Check if a rule matches the action and context."""
        rule_action = rule.get("action")
        
        if isinstance(rule_action, list):
            if action not in rule_action:
                return False
        elif rule_action and rule_action != action:
            return False
        
        # Check constraints
        constraints = rule.get("constraint", [])
        if not isinstance(constraints, list):
            constraints = [constraints] if constraints else []
        
        return self._all_constraints_satisfied(constraints, context)
    
    def _evaluate_permission(
        self,
        permission: Dict[str, Any],
        action: str,
        context: Dict[str, Any]
    ) -> EvaluationResult:
        """Evaluate a single permission rule."""
        rule_action = permission.get("action")
        
        # Check if action matches
        if isinstance(rule_action, list):
            if action not in rule_action:
                return EvaluationResult(
                    allowed=False,
                    reason="Action not in permitted list"
                )
        elif rule_action and rule_action != action:
            return EvaluationResult(
                allowed=False,
                reason=f"Permission is for action '{rule_action}', not '{action}'"
            )
        
        # Check constraints
        constraints = permission.get("constraint", [])
        if not isinstance(constraints, list):
            constraints = [constraints] if constraints else []
        
        if not self._all_constraints_satisfied(constraints, context):
            return EvaluationResult(
                allowed=False,
                reason="Constraints not satisfied"
            )
        
        # Collect duties
        duties = permission.get("duty", [])
        if not isinstance(duties, list):
            duties = [duties] if duties else []
        
        return EvaluationResult(
            allowed=True,
            reason="Permission granted",
            duties=duties
        )
    
    def _all_constraints_satisfied(
        self,
        constraints: List[Dict[str, Any]],
        context: Dict[str, Any]
    ) -> bool:
        """Check if all constraints are satisfied."""
        for constraint in constraints:
            if not self._evaluate_constraint(constraint, context):
                return False
        return True
    
    def _evaluate_constraint(
        self,
        constraint: Dict[str, Any],
        context: Dict[str, Any]
    ) -> bool:
        """Evaluate a single constraint."""
        left_operand = constraint.get("leftOperand")
        operator = constraint.get("operator")
        right_operand = constraint.get("rightOperand")
        
        if not all([left_operand, operator]):
            # Invalid constraint, skip
            return True
        
        # Get value from context
        context_value = context.get(left_operand)
        
        return self._compare(context_value, operator, right_operand)
    
    def _compare(
        self,
        left: Any,
        operator: str,
        right: Any
    ) -> bool:
        """Compare values using ODRL operator."""
        if left is None:
            # No value in context, constraint not satisfied
            return False
        
        if operator == ODRLOperator.EQ or operator == "eq":
            return str(left).lower() == str(right).lower()
        elif operator == ODRLOperator.NEQ or operator == "neq":
            return str(left).lower() != str(right).lower()
        elif operator == ODRLOperator.GT or operator == "gt":
            return float(left) > float(right)
        elif operator == ODRLOperator.GTE or operator == "gteq":
            return float(left) >= float(right)
        elif operator == ODRLOperator.LT or operator == "lt":
            return float(left) < float(right)
        elif operator == ODRLOperator.LTE or operator == "lteq":
            return float(left) <= float(right)
        elif operator == ODRLOperator.IS_A or operator == "isA":
            return str(right).lower() in str(left).lower()
        elif operator == ODRLOperator.IS_ANY_OF or operator == "isAnyOf":
            if isinstance(right, list):
                return str(left) in [str(r) for r in right]
            return str(left) == str(right)
        elif operator == ODRLOperator.IS_NONE_OF or operator == "isNoneOf":
            if isinstance(right, list):
                return str(left) not in [str(r) for r in right]
            return str(left) != str(right)
        
        # Unknown operator, return False for safety
        self.logger.warning(f"Unknown ODRL operator: {operator}")
        return False
    
    def create_default_policy(
        self,
        target: str,
        allowed_actions: List[str] = None,
        purpose: str = None
    ) -> Dict[str, Any]:
        """Create a default ODRL policy."""
        if allowed_actions is None:
            allowed_actions = ["use", "read"]
        
        permission = {
            "target": target,
            "action": allowed_actions,
        }
        
        if purpose:
            permission["constraint"] = [{
                "leftOperand": "purpose",
                "operator": "eq",
                "rightOperand": purpose
            }]
        
        return {
            "@context": "http://www.w3.org/ns/odrl.jsonld",
            "@type": "Policy",
            "uid": f"urn:policy:{target}",
            "profile": "http://www.w3.org/ns/odrl/2/",
            "permission": [permission]
        }


# Global evaluator instance
_evaluator: Optional[ODRLEvaluator] = None


def get_odrl_evaluator() -> ODRLEvaluator:
    """Get the global ODRL evaluator instance."""
    global _evaluator
    if _evaluator is None:
        _evaluator = ODRLEvaluator()
    return _evaluator
