"""Simple ODRL policy evaluator middleware."""
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class ODRLEvaluator:
    """Simple ODRL policy evaluator.
    
    This is a basic implementation that checks common ODRL constraints.
    For production, use a proper ODRL engine.
    """
    
    @staticmethod
    def evaluate_policy(policy: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """Evaluate ODRL policy against context.
        
        Args:
            policy: ODRL policy JSON
            context: Evaluation context (user attributes, purpose, etc.)
            
        Returns:
            True if policy permits access, False otherwise
        """
        try:
            # Check if policy has permissions
            permissions = policy.get("permission", [])
            if not permissions:
                logger.warning("No permissions defined in policy")
                return False
            
            # Evaluate each permission
            for permission in permissions:
                if ODRLEvaluator._evaluate_permission(permission, context):
                    return True
            
            return False
            
        except Exception as e:
            logger.exception(f"Error evaluating policy: {e}")
            return False
    
    @staticmethod
    def _evaluate_permission(permission: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """Evaluate a single permission."""
        # Check action
        action = permission.get("action")
        required_action = context.get("action")
        
        if action and required_action and action != required_action:
            logger.debug(f"Action mismatch: {action} != {required_action}")
            return False
        
        # Check constraints
        constraints = permission.get("constraint", [])
        if not constraints:
            # No constraints, permission granted
            return True
        
        for constraint in constraints:
            if not ODRLEvaluator._evaluate_constraint(constraint, context):
                return False
        
        return True
    
    @staticmethod
    def _evaluate_constraint(constraint: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """Evaluate a single constraint."""
        left_operand = constraint.get("leftOperand")
        operator = constraint.get("operator")
        right_operand = constraint.get("rightOperand")
        
        if not all([left_operand, operator, right_operand]):
            logger.warning("Incomplete constraint definition")
            return False
        
        # Get value from context
        context_value = context.get(left_operand)
        
        # Evaluate based on operator
        if operator == "eq":
            return context_value == right_operand
        elif operator == "neq":
            return context_value != right_operand
        elif operator == "lt":
            return context_value < right_operand
        elif operator == "lteq":
            return context_value <= right_operand
        elif operator == "gt":
            return context_value > right_operand
        elif operator == "gteq":
            return context_value >= right_operand
        elif operator == "in":
            return context_value in right_operand
        else:
            logger.warning(f"Unknown operator: {operator}")
            return False


def check_policy_access(policy: Optional[Dict[str, Any]], user_context: Dict[str, Any]) -> bool:
    """Check if user has access based on policy.
    
    Args:
        policy: ODRL policy or None (if None, access is granted)
        user_context: User context for evaluation
        
    Returns:
        True if access granted, False otherwise
    """
    if not policy:
        # No policy means public access
        return True
    
    return ODRLEvaluator.evaluate_policy(policy, user_context)
