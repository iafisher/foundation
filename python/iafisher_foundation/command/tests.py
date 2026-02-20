import pprint
from typing import Annotated

from expecttest import TestCase

from ..prelude import *

from .command import CmdError, Command, Extra, Group, Mutex, dispatch, _parse


def parse(cmd_or_group: Any, *, argv: List[str]) -> Tuple[Any, Dict[str, Any]]:
    # `command.parse` calls `sys.exit`, which we don't want to do in tests
    handler, result = _parse(cmd_or_group, argv, 1)
    return handler, {**result.args, **result.kwargs}


class Test(TestCase):
    def test_from_function(self):
        def f(
            a_positional_arg: str,
            a_positional_switch: bool,
            *,
            a_required_flag: int,
            an_optional_flag: Optional[str],
            a_flag_with_a_default: int = 42
        ) -> Any:
            return dict(
                a_positional_arg=a_positional_arg,
                a_positional_switch=a_positional_switch,
                a_required_flag=a_required_flag,
                an_optional_flag=an_optional_flag,
                a_flag_with_a_default=a_flag_with_a_default,
            )

        cmd = Command.from_function(f)
        self.assertExpectedInline(
            pprint.pformat(cmd._positionals),
            """\
[ArgSpec(name='a_positional_arg',
         n=<ArgCount.ONE: 'one'>,
         required=True,
         default=Nothing(),
         help='',
         converter=<class 'str'>,
         dest='a_positional_arg')]""",
        )
        self.assertExpectedInline(
            pprint.pformat(cmd._flags),
            """\
{'-a-flag-with-a-default': ArgSpec(name='-a-flag-with-a-default',
                                   n=<ArgCount.ONE: 'one'>,
                                   required=False,
                                   default=42,
                                   help='(default: 42)',
                                   converter=<class 'int'>,
                                   dest='a_flag_with_a_default'),
 '-a-positional-switch': ArgSpec(name='-a-positional-switch',
                                 n=<ArgCount.ZERO: 'zero'>,
                                 required=False,
                                 default=False,
                                 help='',
                                 converter=None,
                                 dest='a_positional_switch'),
 '-a-required-flag': ArgSpec(name='-a-required-flag',
                             n=<ArgCount.ONE: 'one'>,
                             required=True,
                             default=Nothing(),
                             help='',
                             converter=<class 'int'>,
                             dest='a_required_flag'),
 '-an-optional-flag': ArgSpec(name='-an-optional-flag',
                              n=<ArgCount.ONE: 'one'>,
                              required=False,
                              default=None,
                              help='',
                              converter=<class 'str'>,
                              dest='an_optional_flag')}""",
        )
        result = dispatch(
            cmd, argv=["cmd", "arg1", "-a-required-flag", "2"], bail_on_error=False
        )
        self.assertExpectedInline(
            pprint.pformat(result),
            """\
{'a_flag_with_a_default': 42,
 'a_positional_arg': 'arg1',
 'a_positional_switch': False,
 'a_required_flag': 2,
 'an_optional_flag': None}""",
        )
        result = dispatch(
            cmd,
            argv=[
                "cmd",
                "arg1",
                "-a-required-flag",
                "2",
                "-a-flag-with-a-default",
                "-1",
                "-a-positional-switch",
                "-an-optional-flag",
                "flag2",
            ],
            bail_on_error=False,
        )
        self.assertExpectedInline(
            pprint.pformat(result),
            """\
{'a_flag_with_a_default': -1,
 'a_positional_arg': 'arg1',
 'a_positional_switch': True,
 'a_required_flag': 2,
 'an_optional_flag': 'flag2'}""",
        )

    def test_multi_flag(self):
        def f(*, words: List[str] = []) -> Any:
            return dict(words=words)

        cmd = Command.from_function(f)
        self.assertExpectedInline(
            pprint.pformat(cmd._flags),
            """\
{'-words': ArgSpec(name='-words',
                   n=<ArgCount.MANY: 'many'>,
                   required=False,
                   default=[],
                   help='(default: [])',
                   converter=<class 'str'>,
                   dest='words')}""",
        )
        result = dispatch(
            cmd, argv=["cmd", "-words", "one", "two"], bail_on_error=False
        )
        self.assertExpectedInline(
            pprint.pformat(result), """{'words': ['one', 'two']}"""
        )

    def test_parse(self):
        def main_jobs_list(*, verbose: bool) -> Any:
            return dict(subcmd="jobs list", verbose=verbose)

        def main_jobs_schedule(
            *,
            at: Annotated[Optional[str], Extra(help="Run at a particular time")],
            every: Annotated[Optional[str], Extra(help="Run at every interval")],
            cmd: List[str]
        ) -> Any:
            return dict(subcmd="jobs schedule", at=at, every=every, cmd=cmd)

        jobs_cmd = Group(help="Manage background jobs.")
        jobs_cmd.add2("list", main_jobs_list)
        jobs_cmd.add2("schedule", main_jobs_schedule, help="Schedule a job to run.")

        cmd = Group()
        cmd.add("jobs", jobs_cmd)

        argv = ["kg", "jobs", "list"]
        _, args = parse(cmd, argv=argv)
        self.assertEqual({"verbose": False}, args)
        result = dispatch(cmd, argv=argv)
        self.assertExpectedInline(
            pprint.pformat(result), """{'subcmd': 'jobs list', 'verbose': False}"""
        )

        argv = ["kg", "jobs", "schedule", "-at", "8am", "-cmd", "foo"]
        _, args = parse(cmd, argv=argv)
        self.assertEqual({"at": "8am", "cmd": ["foo"], "every": None}, args)
        result = dispatch(cmd, argv=argv)
        self.assertExpectedInline(
            pprint.pformat(result),
            """{'at': '8am', 'cmd': ['foo'], 'every': None, 'subcmd': 'jobs schedule'}""",
        )

    def test_parse2(self):
        def f(words: List[str], *, n: bool, file: Optional[str]) -> Any:
            return dict(words=words, n=n, file=file)

        cmd = Command.from_function(f)

        _, args = parse(cmd, argv=["echo", "-file=example.txt", "hello"])
        self.assertEqual({"file": "example.txt", "n": False, "words": ["hello"]}, args)

        _, args = parse(cmd, argv=["echo", "-n=false", "-file=example.txt", "hello"])
        self.assertEqual({"file": "example.txt", "n": False, "words": ["hello"]}, args)

        _, args = parse(cmd, argv=["echo", "--", "hello"])
        self.assertEqual({"file": None, "n": False, "words": ["hello"]}, args)

        _, args = parse(cmd, argv=["echo", "--", "hello", "-a"])
        self.assertEqual({"file": None, "n": False, "words": ["hello", "-a"]}, args)

        _, args = parse(cmd, argv=["echo", "-file", "-", "--", "hello", "-a"])
        self.assertEqual({"file": "-", "n": False, "words": ["hello", "-a"]}, args)

    def test_optional_positional(self):
        def f(a: Optional[str]) -> Any:
            return dict(a=a)

        cmd = Command.from_function(f)
        result = dispatch(cmd, argv=["my-cmd"], bail_on_error=False)
        self.assertExpectedInline(pprint.pformat(result), """{'a': None}""")

        result = dispatch(cmd, argv=["my-cmd", "arg"], bail_on_error=False)
        self.assertExpectedInline(pprint.pformat(result), """{'a': 'arg'}""")

    def test_mutex(self):
        mutex = Mutex()

        def f(
            *,
            show_all: Annotated[bool, Extra(mutex=mutex)],
            show: Annotated[Optional[str], Extra(mutex=mutex)]
        ) -> Any:
            return dict(show_all=show_all, show=show)

        cmd = Command.from_function(f)
        result = dispatch(cmd, argv=["my-cmd", "-show-all"], bail_on_error=False)
        self.assertExpectedInline(
            pprint.pformat(result), """{'show': None, 'show_all': True}"""
        )
        result = dispatch(
            cmd, argv=["my-cmd", "-show", "this one"], bail_on_error=False
        )
        self.assertExpectedInline(
            pprint.pformat(result), """{'show': 'this one', 'show_all': False}"""
        )

        with self.assertRaisesRegex(
            CmdError, "exactly one of the following is required: -show-all, -show"
        ):
            parse(cmd, argv=["my-cmd"])

        with self.assertRaisesRegex(
            CmdError, "-show-all and -show are mutually exclusive"
        ):
            parse(cmd, argv=["my-cmd", "-show-all", "-show", "this one"])

    def test_mutex_optional(self):
        mutex = Mutex(optional=True)

        def f(
            *,
            show_all: Annotated[bool, Extra(mutex=mutex)],
            show: Annotated[Optional[str], Extra(mutex=mutex)]
        ) -> Any:
            return dict(show_all=show_all, show=show)

        cmd = Command.from_function(f)
        result = dispatch(cmd, argv=["my-cmd", "-show-all"], bail_on_error=False)
        self.assertExpectedInline(
            pprint.pformat(result), """{'show': None, 'show_all': True}"""
        )
        result = dispatch(
            cmd, argv=["my-cmd", "-show", "this one"], bail_on_error=False
        )
        self.assertExpectedInline(
            pprint.pformat(result), """{'show': 'this one', 'show_all': False}"""
        )

        result = dispatch(cmd, argv=["my-cmd"], bail_on_error=False)
        self.assertExpectedInline(
            pprint.pformat(result), """{'show': None, 'show_all': False}"""
        )

        with self.assertRaisesRegex(
            CmdError, "-show-all and -show are mutually exclusive"
        ):
            parse(cmd, argv=["my-cmd", "-show-all", "-show", "this one"])

    def test_mutex_must_appear_on_two_flags(self):
        mutex = Mutex()

        def f(*, limit: Annotated[Optional[int], Extra(mutex=mutex)]) -> Any:
            return dict(limit=limit)

        with self.assertRaisesRegex(
            CmdError, "mutex must appear on at least two flags"
        ):
            Command.from_function(f)

    def test_mutex_flag_must_be_optional(self):
        mutex = Mutex()

        def f(
            *,
            show_all: Annotated[bool, Extra(mutex=mutex)],
            show: Annotated[str, Extra(mutex=mutex)]
        ) -> Any:
            return dict(show_all=show_all, show=show)

        with self.assertRaisesRegex(CmdError, "mutex flag must be optional"):
            Command.from_function(f)

    def test_mutex_is_not_allowed_on_positional(self):
        mutex = Mutex()

        def f(
            x: Annotated[Optional[int], Extra(mutex=mutex)],
            *,
            y: Annotated[Optional[int], Extra(mutex=mutex)]
        ) -> Any:
            return dict(x=x, y=y)

        with self.assertRaisesRegex(
            CmdError, "`extra.mutex` is invalid for positional arguments"
        ):
            Command.from_function(f)

    def test_required_positional_after_optional_is_illegal(self):
        def f(a: Optional[str], b: str) -> Any:
            return dict(a=a, b=b)

        with self.assertRaises(CmdError):
            Command.from_function(f)

    def test_optional_positional_after_requred_is_ok(self):
        def f(a: str, b: Optional[str]) -> Any:
            return dict(a=a, b=b)

        cmd = Command.from_function(f)
        result = dispatch(cmd, argv=["my-cmd", "arg"], bail_on_error=False)
        self.assertExpectedInline(pprint.pformat(result), """{'a': 'arg', 'b': None}""")

        result = dispatch(cmd, argv=["my-cmd", "arg", "arg2"], bail_on_error=False)
        self.assertExpectedInline(
            pprint.pformat(result), """{'a': 'arg', 'b': 'arg2'}"""
        )

    def test_passthrough(self):
        def f(args: Annotated[List[str], Extra(passthrough=True)]) -> Any:
            return dict(args=args)

        cmd = Command.from_function(f)
        result = dispatch(
            cmd,
            argv=["my-cmd", "restic", "--dry-run", "/home/user/documents"],
            bail_on_error=False,
        )
        self.assertExpectedInline(
            pprint.pformat(result),
            """{'args': ['restic', '--dry-run', '/home/user/documents']}""",
        )

    def test_converter(self):
        def f(
            x: Annotated[datetime.date, Extra(converter=datetime.date.fromisoformat)]
        ) -> Any:
            return dict(x=x)

        cmd = Command.from_function(f)

        result = dispatch(
            cmd,
            argv=["my-cmd", "2025-01-01"],
            bail_on_error=False,
        )
        self.assertExpectedInline(
            pprint.pformat(result),
            """{'x': datetime.date(2025, 1, 1)}""",
        )

    def test_negative_number(self):
        def f(*, limit: int, temperature: float) -> Any:
            return dict(limit=limit, temperature=temperature)

        # regression test for 2026 bug #004
        cmd = Command.from_function(f)
        result = dispatch(
            cmd,
            argv=["my-cmd", "-limit", "-1", "-temperature", "-1.5"],
            bail_on_error=False,
        )
        self.assertExpectedInline(
            pprint.pformat(result), """{'limit': -1, 'temperature': -1.5}"""
        )

    def test_repeated(self):
        def f(*, verbose: bool, src: Optional[str], recipient: List[str]) -> Any:
            return dict(verbose=verbose, src=src, recipient=recipient)

        cmd = Command.from_function(f)

        with self.assertRaises(CmdError):
            parse(cmd, argv=["cmd", "-verbose", "-verbose"])

        with self.assertRaises(CmdError):
            parse(cmd, argv=["cmd", "-src", "a", "-src", "b"])

        with self.assertRaises(CmdError):
            parse(cmd, argv=["cmd", "-recipient", "a", "-recipient", "b"])

    def test_passthrough_must_be_list_of_str(self):
        def f(args: Annotated[str, Extra(passthrough=True)]) -> Any:
            return dict(args=args)

        with self.assertRaisesRegex(CmdError, r"List\[str\]"):
            Command.from_function(f)

    def test_passthrough_must_be_positional(self):
        def f(*, args: Annotated[str, Extra(passthrough=True)]) -> Any:
            return dict(args=args)

        with self.assertRaisesRegex(CmdError, "must be positional"):
            Command.from_function(f)

    def test_error_includes_function_and_param_name(self):
        # invalid: conflicting defaults
        def my_special_function(my_param: Annotated[int, Extra(default=2)] = 3) -> Any:
            return dict(my_param=my_param)

        with self.assertRaisesRegex(
            CmdError,
            "duplicate defaults.*function: my_special_function, param: my_param",
        ):
            Command.from_function(my_special_function)

    def test_invalid_type(self):
        def f(x: Dict[str, str]) -> Any:
            return dict(x=x)

        with self.assertRaisesRegex(CmdError, "type `.*Dict.*` is not supported"):
            Command.from_function(f)

    def test_parameter_must_have_annotation(self):
        def f(x) -> Any:  # type: ignore
            return dict(x=x)  # type: ignore

        with self.assertRaisesRegex(CmdError, "missing type annotation"):
            Command.from_function(f)

    def test_list_positional_must_be_last(self):
        def f(words: List[str], junk: str) -> Any:
            return dict(words=words, junk=junk)

        with self.assertRaisesRegex(CmdError, "list positional argument must be last"):
            Command.from_function(f)
