import pytest

from tri_declarative import (
    evaluate,
    evaluate_recursive,
    filter_show_recursive,
    get_signature,
    matches,
    remove_show_recursive,
    evaluate_strict,
    evaluate_recursive_strict,
    should_show,
    get_callable_description,
    Namespace,
)


def test_evaluate_recursive():
    foo = {
        'foo': {'foo': lambda x: x * 2},
        'bar': [{'foo': lambda x: x * 2}],
        'baz': {lambda x: x * 2},
        'boo': 17
    }

    assert evaluate_recursive(foo, x=2) == {
        'foo': {'foo': 4},
        'bar': [{'foo': 4}],
        'baz': {4},
        'boo': 17,
    }


def test_remove_and_filter_show_recursive():
    class Foo:
        show = False

    assert remove_show_recursive(filter_show_recursive({
        'foo': [Foo(), {'show': False}, {'bar'}, {}, {'show': True}],
        'bar': {'show': False},
        'baz': Foo(),
        'asd': {Foo(), 'bar'},
        'qwe': {'show': True},
        'quux': {'show': None},
    })) == ({
        'foo': [{'bar'}, {}, {}],
        'asd': {'bar'},
        'qwe': {},
    })


def test_should_show():
    class Foo:
        show = False

    assert should_show(Foo()) is False
    assert should_show(Foo) is False
    assert should_show(dict(show=False)) is False
    assert should_show(dict(show=True)) is True
    assert should_show(dict(show=[])) == []

    with pytest.raises(AssertionError) as e:
        assert should_show(dict(show=lambda: True))

    assert str(e.value) == '`show` was a callable. You probably forgot to evaluate it. The callable was: lambda found at: `assert should_show(dict(show=lambda: True))`'


def test_no_evaluate_kwargs_mismatch():
    def f(x):
        return x * 2

    assert evaluate(f) is f
    assert evaluate(f, y=1) is f


def test_get_signature():
    def f(a, b):
        pass

    def f2(b, a):
        pass

    assert get_signature(lambda a, b: None) == get_signature(f2) == get_signature(f) == 'a,b||'
    assert f.__tri_declarative_signature == 'a,b||'


def test_get_signature_fails_on_native():
    # isinstance will return False for a native function. A string will also return False.
    f = 'this is not a function'
    assert get_signature(f) is None


def test_get_signature_on_class():
    class Foo:
        def __init__(self, a, b):
            pass

    assert 'a,b,self||' == get_signature(Foo)
    assert 'a,b,self||' == Foo.__tri_declarative_signature


def test_get_signature_varargs():
    assert get_signature(lambda a, b, **c: None) == "a,b||*"


def test_evaluate_subset_parameters():
    def f(x, **_):
        return x

    assert evaluate(f, x=17, y=42) == 17


def test_match_caching():
    assert matches("a,b", "a,b||")
    assert matches("a,b", "a||*")
    assert not matches("a,b", "c||*")
    assert matches("a,b", "a||*")
    assert not matches("a,b", "c||*")


def test_get_signature_description():
    assert get_signature(lambda a, b: None) == 'a,b||'
    assert get_signature(lambda a, b, c, d=None, e=None: None) == 'a,b,c|d,e|'
    assert get_signature(lambda d, c, b=None, a=None: None) == 'c,d|a,b|'
    assert get_signature(lambda a, b, c=None, d=None, **_: None) == 'a,b|c,d|*'
    assert get_signature(lambda d, c, b=None, a=None, **_: None) == 'c,d|a,b|*'
    assert get_signature(lambda **_: None) == '||*'


def test_match_optionals():
    assert matches("a,b", "a,b||")
    assert matches("a,b", "a,b|c|")
    assert matches("a,b,c", "a,b|c|")
    assert matches("a,b,c", "a,b|c,d|")
    assert matches("a,b", "a,b|c|*")
    assert not matches("a,b,d", "a,b|c|")
    assert matches("a,b,d", "a,b|c|*")
    assert matches("", "||")
    assert not matches("a", "||")


def test_match_special_case():
    assert not matches("", "||*")
    assert not matches("a,b,c", "||*")


def test_evaluate_extra_kwargs_with_defaults():
    def f(x, y=17):
        return x

    assert evaluate(f, x=17) == 17


def test_evaluate_on_methods():
    class Foo:
        def bar(self, x):
            return x

        @staticmethod
        def baz(x):
            return x

    assert evaluate(Foo().bar, x=17) == 17
    assert evaluate(Foo().baz, x=17) == 17

    f = Foo().bar
    assert evaluate(f, y=17) is f


def test_early_return_from_get_signature():
    def foo(a, b, c):
        pass

    object.__setattr__(foo, '__tri_declarative_signature', 'foobar')
    assert get_signature(foo) == 'foobar'


def test_evaluate_strict():
    with pytest.raises(AssertionError) as e:
        evaluate_strict(lambda foo: 1, bar=2, baz=4)

    assert str(e.value) == "Evaluating lambda found at: `evaluate_strict(lambda foo: 1, bar=2, baz=4)` didn't resolve it into a value but strict mode was active, the signature doesn't match the given parameters. Note that you must match at least one keyword argument. We had these arguments: bar, baz"


def test_evaluate_recursive_strict():
    with pytest.raises(AssertionError) as e:
        evaluate_recursive_strict(dict(foo=lambda foo: 1), bar=2, baz=4)

    assert str(e.value) == "Evaluating lambda found at: `evaluate_recursive_strict(dict(foo=lambda foo: 1), bar=2, baz=4)` didn't resolve it into a value but strict mode was active, the signature doesn't match the given parameters. Note that you must match at least one keyword argument. We had these arguments: bar, baz"


def test_non_strict_evaluate():
    def foo(bar):
        return bar

    assert evaluate(foo, bar=True) is True  # first the evaluated case
    assert evaluate(foo, quuz=True) is foo  # now we missed the signature, so we get the function unevaluated back


def test_get_callable_description():
    # noinspection PyUnusedLocal
    def foo(a, b, c, *, bar, **kwargs):
        pass

    description = get_callable_description(foo)
    assert description.startswith('`<function test_get_callable_description.<locals>.foo at')
    assert description.endswith('`')


def test_get_callable_description_nested_lambda():
    foo = Namespace(bar=lambda x: x)

    description = get_callable_description(foo)
    assert description.startswith('`Namespace(bar=<function test_get_callable_description_nested_lambda.<locals>.<lambda> at')
    assert description.endswith('`')
