"""Unit tests for the SafeExpressionEvaluator."""

import pytest

from nim_audit.utils.expression import SafeExpressionEvaluator, safe_eval


class TestSafeExpressionEvaluator:
    """Tests for SafeExpressionEvaluator."""

    @pytest.fixture
    def evaluator(self):
        """Create an evaluator instance."""
        return SafeExpressionEvaluator()

    @pytest.fixture
    def sample_context(self):
        """Create a sample context for evaluation."""
        return {
            "labels": {
                "com.nvidia.nim.version": "1.5.0",
                "com.nvidia.nim.model.name": "llama3",
            },
            "env": {
                "NIM_SERVER_PORT": "8000",
                "NIM_LOG_LEVEL": "INFO",
            },
            "exposed_ports": [8000, 8080],
            "name": "test-image",
            "count": 42,
        }

    def test_evaluate_literal_string(self, evaluator):
        """Test evaluating string literals."""
        assert evaluator.evaluate("'hello'", {}) == "hello"
        assert evaluator.evaluate('"world"', {}) == "world"

    def test_evaluate_literal_numbers(self, evaluator):
        """Test evaluating number literals."""
        assert evaluator.evaluate("42", {}) == 42
        assert evaluator.evaluate("3.14", {}) == 3.14
        assert evaluator.evaluate("-5", {}) == -5

    def test_evaluate_literal_booleans(self, evaluator):
        """Test evaluating boolean literals."""
        assert evaluator.evaluate("True", {}) is True
        assert evaluator.evaluate("False", {}) is False

    def test_evaluate_none(self, evaluator):
        """Test evaluating None."""
        assert evaluator.evaluate("None", {}) is None

    def test_evaluate_variable(self, evaluator, sample_context):
        """Test evaluating variables from context."""
        assert evaluator.evaluate("name", sample_context) == "test-image"
        assert evaluator.evaluate("count", sample_context) == 42

    def test_evaluate_dict_get(self, evaluator, sample_context):
        """Test dict.get() method."""
        assert evaluator.evaluate(
            "labels.get('com.nvidia.nim.version')", sample_context
        ) == "1.5.0"
        assert evaluator.evaluate(
            "labels.get('nonexistent', 'default')", sample_context
        ) == "default"

    def test_evaluate_dict_subscript(self, evaluator, sample_context):
        """Test dict subscript access."""
        assert evaluator.evaluate("env['NIM_SERVER_PORT']", sample_context) == "8000"

    def test_evaluate_comparisons(self, evaluator, sample_context):
        """Test comparison operators."""
        assert evaluator.evaluate("count == 42", sample_context) is True
        assert evaluator.evaluate("count != 0", sample_context) is True
        assert evaluator.evaluate("count > 40", sample_context) is True
        assert evaluator.evaluate("count < 50", sample_context) is True
        assert evaluator.evaluate("count >= 42", sample_context) is True
        assert evaluator.evaluate("count <= 42", sample_context) is True

    def test_evaluate_in_operator(self, evaluator, sample_context):
        """Test 'in' operator."""
        assert evaluator.evaluate("8000 in exposed_ports", sample_context) is True
        assert evaluator.evaluate("9000 in exposed_ports", sample_context) is False
        assert evaluator.evaluate("'NIM_SERVER_PORT' in env", sample_context) is True

    def test_evaluate_boolean_and(self, evaluator, sample_context):
        """Test 'and' operator."""
        assert evaluator.evaluate("count > 0 and count < 100", sample_context) is True
        assert evaluator.evaluate("count > 0 and count < 10", sample_context) is False

    def test_evaluate_boolean_or(self, evaluator, sample_context):
        """Test 'or' operator."""
        assert evaluator.evaluate("count > 100 or count < 50", sample_context) is True
        assert evaluator.evaluate("count > 100 or count < 0", sample_context) is False

    def test_evaluate_boolean_not(self, evaluator, sample_context):
        """Test 'not' operator."""
        assert evaluator.evaluate("not False", {}) is True
        assert evaluator.evaluate("not count > 100", sample_context) is True

    def test_evaluate_is_none(self, evaluator, sample_context):
        """Test 'is None' and 'is not None'."""
        sample_context["value"] = None
        assert evaluator.evaluate("value is None", sample_context) is True
        assert evaluator.evaluate("name is not None", sample_context) is True

    def test_evaluate_string_methods(self, evaluator, sample_context):
        """Test allowed string methods."""
        assert evaluator.evaluate("name.startswith('test')", sample_context) is True
        assert evaluator.evaluate("name.endswith('image')", sample_context) is True
        assert evaluator.evaluate("name.upper()", sample_context) == "TEST-IMAGE"

    def test_evaluate_builtin_functions(self, evaluator, sample_context):
        """Test allowed builtin functions."""
        assert evaluator.evaluate("len(exposed_ports)", sample_context) == 2
        assert evaluator.evaluate("str(count)", sample_context) == "42"
        assert evaluator.evaluate("int('100')", {}) == 100
        assert evaluator.evaluate("max([1, 2, 3])", {}) == 3
        assert evaluator.evaluate("min([1, 2, 3])", {}) == 1
        assert evaluator.evaluate("sum([1, 2, 3])", {}) == 6
        assert evaluator.evaluate("abs(-5)", {}) == 5

    def test_evaluate_any_all(self, evaluator):
        """Test any() and all() functions."""
        assert evaluator.evaluate("all([True, True, True])", {}) is True
        assert evaluator.evaluate("all([True, False, True])", {}) is False
        assert evaluator.evaluate("any([False, False, True])", {}) is True
        assert evaluator.evaluate("any([False, False, False])", {}) is False

    def test_evaluate_arithmetic(self, evaluator, sample_context):
        """Test arithmetic operations."""
        assert evaluator.evaluate("count + 8", sample_context) == 50
        assert evaluator.evaluate("count - 2", sample_context) == 40
        assert evaluator.evaluate("count * 2", sample_context) == 84
        assert evaluator.evaluate("count / 2", sample_context) == 21.0
        assert evaluator.evaluate("count % 5", sample_context) == 2

    def test_evaluate_list_literal(self, evaluator):
        """Test list literals."""
        assert evaluator.evaluate("[1, 2, 3]", {}) == [1, 2, 3]
        assert evaluator.evaluate("['a', 'b']", {}) == ["a", "b"]

    def test_evaluate_dict_literal(self, evaluator):
        """Test dict literals."""
        assert evaluator.evaluate("{'a': 1, 'b': 2}", {}) == {"a": 1, "b": 2}

    def test_evaluate_ternary(self, evaluator, sample_context):
        """Test ternary if expression."""
        assert evaluator.evaluate("'high' if count > 10 else 'low'", sample_context) == "high"
        assert evaluator.evaluate("'low' if count > 100 else 'normal'", sample_context) == "normal"

    def test_evaluate_list_comprehension(self, evaluator):
        """Test simple list comprehension."""
        assert evaluator.evaluate("[x * 2 for x in [1, 2, 3]]", {}) == [2, 4, 6]
        assert evaluator.evaluate("[x for x in [1, 2, 3, 4] if x > 2]", {}) == [3, 4]

    def test_evaluate_chained_comparison(self, evaluator, sample_context):
        """Test chained comparisons."""
        assert evaluator.evaluate("10 < count < 100", sample_context) is True
        assert evaluator.evaluate("50 < count < 100", sample_context) is False

    def test_evaluate_complex_policy_condition(self, evaluator, sample_context):
        """Test complex conditions like those in policy rules."""
        # Rule: NIM version must exist
        assert evaluator.evaluate(
            "labels.get('com.nvidia.nim.version') is not None",
            sample_context,
        ) is True

        # Rule: Port 8000 must be exposed
        assert evaluator.evaluate(
            "8000 in exposed_ports or 80 in exposed_ports",
            sample_context,
        ) is True

        # Rule: No sensitive env vars (using list comprehension instead of generator)
        assert evaluator.evaluate(
            "not any([k in ['PASSWORD', 'SECRET'] for k in list(env.keys())])",
            sample_context,
        ) is True

    def test_evaluate_unknown_variable_raises(self, evaluator):
        """Test that unknown variables raise ValueError."""
        with pytest.raises(ValueError, match="Unknown variable"):
            evaluator.evaluate("unknown_var", {})

    def test_evaluate_invalid_syntax_raises(self, evaluator):
        """Test that invalid syntax raises ValueError."""
        with pytest.raises(ValueError, match="Invalid expression syntax"):
            evaluator.evaluate("1 +", {})

    def test_evaluate_deeply_nested_raises(self):
        """Test that deeply nested expressions raise ValueError."""
        evaluator = SafeExpressionEvaluator(max_depth=5)
        # Create a deeply nested expression with actual operations
        # Each operation adds depth, so we need nested operations
        deep = "[[[[[[[[1]]]]]]]]"  # Nested lists increase depth
        with pytest.raises(ValueError, match="too deeply nested"):
            evaluator.evaluate(deep, {})

    def test_safe_eval_function(self, sample_context):
        """Test the convenience safe_eval function."""
        assert safe_eval("count > 0", sample_context) is True
        assert safe_eval("labels.get('com.nvidia.nim.version')", sample_context) == "1.5.0"


class TestSafeEvalPolicyRules:
    """Test safe_eval with real policy rule conditions."""

    @pytest.fixture
    def image_context(self):
        """Create an image-like context."""
        return {
            "labels": {
                "com.nvidia.nim.version": "1.5.0",
                "com.nvidia.nim.model.name": "llama3-8b",
            },
            "env": {
                "NIM_SERVER_PORT": "8000",
                "NIM_MAX_BATCH_SIZE": "16",
            },
            "exposed_ports": [8000],
            "config": {"User": "nim"},
        }

    def test_require_version_label(self, image_context):
        """Test rule: require-version-label."""
        condition = "labels.get('com.nvidia.nim.version') is not None"
        assert safe_eval(condition, image_context) is True

        # Test failure case
        del image_context["labels"]["com.nvidia.nim.version"]
        assert safe_eval(condition, image_context) is False

    def test_no_root_user(self, image_context):
        """Test rule: no-root-user."""
        condition = "config.get('User', 'root') != 'root' and config.get('User', '') != ''"
        assert safe_eval(condition, image_context) is True

        # Test failure case
        image_context["config"]["User"] = "root"
        assert safe_eval(condition, image_context) is False

    def test_check_exposed_ports(self, image_context):
        """Test rule: check-exposed-ports."""
        condition = "8000 in exposed_ports or 80 in exposed_ports"
        assert safe_eval(condition, image_context) is True

        # Test failure case
        image_context["exposed_ports"] = [9000]
        assert safe_eval(condition, image_context) is False

    def test_batch_size_check(self, image_context):
        """Test rule: batch-size-check."""
        condition = "int(env.get('NIM_MAX_BATCH_SIZE', '1')) <= 64"
        assert safe_eval(condition, image_context) is True

        # Test failure case
        image_context["env"]["NIM_MAX_BATCH_SIZE"] = "128"
        assert safe_eval(condition, image_context) is False
