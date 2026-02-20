"""
Command-line argument parsing library with type inference from function signatures.

Use `Command.from_function()` to create commands from annotated functions, or
`Group.add2()` to add subcommands directly from functions.
"""

import decimal
import inspect
import logging
import subprocess
import textwrap
import traceback
import types
import typing
import uuid

from .. import colors, tabular, timehelper
from ..prelude import *


class ArgCount(enum.Enum):
    ZERO = "zero"
    ONE = "one"
    MANY = "many"


ConverterType = Callable[[str], Any]


@dataclass
class ArgSpec:
    name: str
    n: ArgCount
    required: bool
    default: Any
    help: str
    converter: Optional[ConverterType]
    dest: str


Handler = Callable[..., Any]


@dataclass
class TypeAnnotation:
    """
    The internal representation of a function parameter's type annotation.

    Example:

        lucky_numbers: Annotated[Optional[List[int]], Extra(...)] = [42]

    becomes:

        TypeAnnotation(base_type=int, is_optional=True, is_list=True, default=[42], extra=Extra(...))

    """

    base_type: Any
    is_optional: bool
    is_list: bool
    # taken either from the type annotation itself, or from `extra`; equal to `NOTHING` if not given
    default: Any
    extra: "Extra"
    arg_type: typing.Literal["arg", "switch", "flag"]

    @classmethod
    def from_param(cls, param: inspect.Parameter) -> "TypeAnnotation":
        if param.annotation is inspect.Signature.empty:
            raise CmdError("missing type annotation")

        if param.kind == inspect.Parameter.VAR_POSITIONAL:
            raise CmdError(
                "variable positional arguments (e.g., `*args`) are not allowed;"
                " use `args: List[...]` instead"
            )
        elif param.kind == inspect.Parameter.VAR_KEYWORD:
            raise CmdError("`**kwargs` is not supported")

        if _is_annotated_type(param.annotation):
            base_type, extra = typing.get_args(param.annotation)
        else:
            base_type = param.annotation
            extra = Extra()

        if _is_optional_type(base_type):
            args = typing.get_args(base_type)
            base_type = args[0] if args[1] is type(None) else args[1]
            is_optional = True
        else:
            is_optional = False

        if typing.get_origin(base_type) is list:
            base_type = typing.get_args(base_type)[0]
            is_list = True
        else:
            is_list = False

        supported_types = [
            int,
            float,
            str,
            bool,
            StringEnum,
            pathlib.Path,
            decimal.Decimal,
        ]
        if extra.converter is None and (
            typing.get_origin(base_type) is not None
            or not any(issubclass(base_type, t) for t in supported_types)
        ):
            raise CmdError(f"type `{base_type!r}` is not supported")

        if base_type is bool:
            if is_list:
                raise CmdError("`List[bool]` is not allowed")

            if is_optional:
                raise CmdError("use just `bool` instead of `Optional[bool]`")

            arg_type = "switch"
        else:
            match param.kind:
                case (
                    inspect.Parameter.POSITIONAL_ONLY
                    | inspect.Parameter.POSITIONAL_OR_KEYWORD
                ):
                    arg_type = "arg"
                case inspect.Parameter.KEYWORD_ONLY:
                    arg_type = "flag"

        default_given_in_param = param.default is not inspect.Signature.empty
        default_given_in_extra = extra.default is not NOTHING
        match (default_given_in_extra, default_given_in_param):
            case (True, True):
                raise CmdError("duplicate defaults")
            case (True, False):
                default = extra.default
            case (False, True):
                default = param.default
            case (False, False):
                default = NOTHING

        if default is not NOTHING:
            is_optional = True

        if arg_type == "arg":
            if extra.name:
                raise CmdError("`extra.name` is invalid for positional arguments")

            if default is not NOTHING:
                raise CmdError("positional arguments cannot have a default value")

            if extra.passthrough and not (is_list and base_type is str):
                raise CmdError("passthrough argument must have type `List[str]`")

            if extra.mutex is not None:
                raise CmdError("`extra.mutex` is invalid for positional arguments")
        else:
            if extra.passthrough:
                # TODO(2026-02): Seems like a passthrough flag should be allowed.
                raise CmdError("passthrough argument must be positional")

            if extra.mutex is not None and not (arg_type == "switch" or is_optional):
                raise CmdError("mutex flag must be optional")

            if extra.mutex is not None and default is not NOTHING:
                # Semantics of this seem confusing but I'm willing to reconsider if I can come up
                # with a concrete use case.
                raise CmdError("mutex flag cannot have a default")

        return cls(
            base_type=base_type,
            is_optional=is_optional,
            is_list=is_list,
            default=default,
            extra=extra,
            arg_type=arg_type,
        )

    def has_default(self) -> bool:
        return self.default is not inspect.Signature.empty


class Command:
    _handler: Handler
    _names_taken: Set[str]
    _flags: Dict[str, ArgSpec]
    _positionals: List[ArgSpec]
    _passthrough: Optional[str]
    _mutexes: Dict[str, Tuple["Mutex", List[str]]]
    help: str
    description: str
    program: str
    less_logging: bool

    def __init__(
        self,
        handler: Handler,
        *,
        help: str = "",
        description: str = "",
        program: str = "",
        less_logging: bool = True,
    ) -> None:
        self._handler = handler
        self._names_taken = set()
        self._flags = {}
        self._positionals = []
        self._passthrough = None
        self._mutexes = {}
        self.help = help
        self.description = description
        self.program = program
        self.less_logging = less_logging

    @classmethod
    def from_function(
        cls,
        f: Any,
        *,
        help: str = "",
        description: str = "",
        program: str = "",
        less_logging: bool = True,
    ) -> "Command":
        sig = inspect.signature(f)
        cmd = cls(
            f,
            help=help,
            description=description,
            program=program,
            less_logging=less_logging,
        )
        for name, param in sig.parameters.items():
            try:
                type_annotation = TypeAnnotation.from_param(param)
                extra = type_annotation.extra

                if extra.converter is not None:
                    converter = extra.converter
                else:
                    converter = type_annotation.base_type

                dest = name
                flag_name = extra.name or _python_to_flag(name)
                match type_annotation.arg_type:
                    case "switch":
                        cmd._switch(flag_name, help=extra.help, dest=dest)
                    case "flag":
                        cmd._flag(
                            flag_name,
                            n=(
                                ArgCount.MANY
                                if type_annotation.is_list
                                else ArgCount.ONE
                            ),
                            required=not type_annotation.is_optional,
                            default=type_annotation.default,
                            converter=converter,
                            help=extra.help,
                            dest=dest,
                        )
                    case "arg":
                        if extra.passthrough:
                            cmd._add_passthrough(name)
                        else:
                            cmd._arg(
                                name,
                                required=not type_annotation.is_optional,
                                n=(
                                    ArgCount.MANY
                                    if type_annotation.is_list
                                    else ArgCount.ONE
                                ),
                                converter=converter,
                                help=extra.help,
                            )

                if extra.mutex is not None:
                    mutex_id = extra.mutex.mutex_id
                    if mutex_id in cmd._mutexes:
                        cmd._mutexes[mutex_id][1].append(flag_name)
                    else:
                        cmd._mutexes[mutex_id] = (extra.mutex, [flag_name])
            except CmdError as e:
                location = f"function: {f.__name__}, param: {name}"
                raise CmdError(f"{e} ({location})") from e

        cmd._check_all()
        return cmd

    def _switch(self, name: str, *, help: str = "", dest: str = "") -> None:
        self._check(name, is_flag=True, required=False)
        self._flags[name] = ArgSpec(
            name=name,
            n=ArgCount.ZERO,
            required=False,
            default=False,
            help=help,
            converter=None,
            dest=(dest or name),
        )

    def _arg(
        self,
        name: str,
        *,
        required: bool,
        n: ArgCount,
        help: str = "",
        converter: Optional[ConverterType] = None,
    ) -> None:
        self._check(name, is_flag=False, required=required)
        self._positionals.append(
            ArgSpec(
                name=name,
                n=n,
                required=required,
                default=[] if n == ArgCount.MANY else NOTHING,
                help=help,
                converter=converter,
                dest=name,
            )
        )

    def _flag(
        self,
        name: str,
        *,
        n: ArgCount,
        required: bool,
        default: Any = NOTHING,
        help: str = "",
        converter: Optional[ConverterType] = None,
        dest: str = "",
    ) -> None:
        self._check(name, is_flag=True, required=required)

        if default is not NOTHING:
            if isinstance(default, pathlib.Path):
                # Try to format as '~/path/to/file' instead of, e.g., `/Users/iafisher/path/to/file`.
                # This is mainly to make test output not depend on the machine it was run on.
                try:
                    default_relpath = default.relative_to(pathlib.Path.home())
                except ValueError:
                    default_as_str = default.as_posix()
                else:
                    default_as_str = f"~/{default_relpath.as_posix()}"
            else:
                default_as_str = repr(default)

            default_help = f"(default: {default_as_str})"
            if help:
                help += " " + default_help
            else:
                help = default_help

        if default is NOTHING and not required:
            default = [] if n == ArgCount.MANY else None

        self._flags[name] = ArgSpec(
            name=name,
            n=n,
            required=required,
            default=default,
            help=help,
            converter=converter,
            dest=(dest or name),
        )

    def _add_passthrough(self, name: str) -> None:
        # TODO(2025-06): Support this functionality in a more principled way (e.g., allow known
        # flags, or only pass-through args after '--' marker)
        if len(self._flags) > 0 or len(self._positionals) > 0:
            raise CmdError(
                "command with flags or positionals cannot be marked as passthrough"
            )

        self._passthrough = name

    def _check(self, name: str, *, is_flag: bool, required: bool) -> None:
        if self._passthrough is not None:
            raise CmdError("command was already specified as passthrough")

        if name in self._names_taken:
            raise CmdError("duplicate argument name", name)

        if _is_help_flag(name) or _is_version_flag(name):
            raise CmdError("flag name is reserved", name)

        if is_flag and not _is_flag(name):
            raise CmdError(
                "flag name is not valid (does it start with a hyphen?)", name
            )

        if not is_flag and name.startswith("-"):
            raise CmdError("positional name must not start with hyphen", name)

        have_optional_positionals = any(not spec.required for spec in self._positionals)
        if not is_flag and required and have_optional_positionals:
            raise CmdError("required positional argument cannot follow optional", name)

        have_list_positional = any(
            spec.n == ArgCount.MANY for spec in self._positionals
        )
        if not is_flag and have_list_positional:
            raise CmdError("list positional argument must be last")

        self._names_taken.add(name)

    def _check_all(self) -> None:
        for _, mutex_flags in self._mutexes.values():
            if len(mutex_flags) < 2:
                raise CmdError(
                    f"mutex must appear on at least two flags: {mutex_flags}"
                )


class Group:
    subcmds: Dict[str, Union[Command, "Group"]]
    help: str
    description: str
    program: str

    def __init__(
        self, *, help: str = "", description: str = "", program: str = ""
    ) -> None:
        self.subcmds = {}
        self.help = help
        self.description = description
        self.program = program

    def add(self, name: str, cmd_or_group: Union[Command, "Group"]) -> None:
        if name in self.subcmds:
            raise CmdError("duplicate subcommand", name)

        self.subcmds[name] = cmd_or_group

    def add2(
        self,
        name: str,
        f: Callable[..., Any],
        help: str = "",
        description: str = "",
        program: str = "",
        less_logging: bool = True,
    ) -> None:
        self.add(
            name,
            Command.from_function(
                f,
                help=help,
                description=description,
                program=program,
                less_logging=less_logging,
            ),
        )


def dispatch(
    cmd_or_group: Union[Command, Group],
    *,
    argv: Optional[List[str]] = None,
    bail_on_error: bool = True,
    log_init: Optional[Callable[[int], None]] = None,
) -> Any:
    if argv is None:
        argv = sys.argv

    try:
        handler, parse_result = parse(
            cmd_or_group, argv=argv, bail_on_error=bail_on_error
        )
    except CmdHelpError as e:
        program_name = None
        if cmd_or_group.program:
            program_name = cmd_or_group.program
        else:
            program_name = os.environ.get("KG_PROGRAM_NAME", argv[0])

        program = " ".join([program_name] + argv[1 : e.index])
        print(get_help_text(e.cmd_or_group, program=program))
        if e.message:
            print()
            colors.error(e.message)
            sys.exit(1)
    except CmdVersionError:
        print(get_version())
    else:
        if log_init is not None:
            env_log_level = os.environ.get("KG_LOG_LEVEL", "").lower()
            if env_log_level:
                if env_log_level == "error":
                    loglevel = logging.ERROR
                elif env_log_level in ("warn", "warning"):
                    loglevel = logging.WARN
                elif env_log_level == "info":
                    loglevel = logging.INFO
                elif env_log_level == "debug":
                    loglevel = logging.DEBUG
                else:
                    raise KgError("unknown log level", s=env_log_level)
            else:
                loglevel = logging.WARN if parse_result.less_logging else logging.INFO

            log_init(loglevel)

        try:
            return handler(*parse_result.args.values(), **parse_result.kwargs)
        except Exception as e:
            if isinstance(e, KgError) and parse_result.less_logging:
                eprint(traceback.format_exc(), end="", flush=True)
                eprint()
                eprint("The command failed due to a Python exception.")
                eprint()
                eprint(textwrap.indent(e.to_human_str(), prefix="  "))
                eprint()
                sys.exit(1)
            else:
                raise e

    return None


@dataclass
class ParseResult:
    args: Dict[str, Any]
    kwargs: Dict[str, Any]
    less_logging: bool


def parse(
    cmd_or_group: Union[Command, Group],
    *,
    argv: List[str],
    bail_on_error: bool = True,
) -> Tuple[Handler, ParseResult]:
    index = 1
    try:
        return _parse(cmd_or_group, argv, index)
    except CmdError as e:
        if bail_on_error:
            print(f"Command-line error: {e}", file=sys.stderr)
            sys.exit(1)
        else:
            raise e


def _parse(
    cmd_or_group: Union[Command, Group], argv: List[str], index: int
) -> Tuple[Handler, ParseResult]:
    if isinstance(cmd_or_group, Command):
        return _parse_command(cmd_or_group, argv, index)
    else:
        return _parse_group(cmd_or_group, argv, index)


@dataclass
class SpecAndValue:
    spec: ArgSpec
    value: Any
    is_set: bool


def _parse_command(
    cmd: Command, argv: List[str], index: int
) -> Tuple[Handler, ParseResult]:
    if cmd._passthrough is not None:
        return cmd._handler, ParseResult(
            args={cmd._passthrough: argv[index:]},
            kwargs={},
            less_logging=cmd.less_logging,
        )

    flags_to_parse: Dict[str, SpecAndValue] = {}
    positionals_to_parse: List[SpecAndValue] = []
    positionals_index = 0

    @dataclass
    class MutexState:
        satisfied: Optional[str]  # the name of the flag that satisfied it
        optional: bool
        eligible_flags: List[str]

    mutexes = {
        mutex_id: MutexState(
            satisfied=None, optional=mutex.optional, eligible_flags=eligible_flags
        )
        for mutex_id, (mutex, eligible_flags) in cmd._mutexes.items()
    }
    flag_to_mutex_id = {
        name: mutex.mutex_id for mutex, names in cmd._mutexes.values() for name in names
    }

    for spec in cmd._flags.values():
        s_and_v = SpecAndValue(spec=spec, value=spec.default, is_set=False)
        flags_to_parse[spec.name] = s_and_v

    for spec in cmd._positionals:
        positionals_to_parse.append(
            SpecAndValue(spec=spec, value=spec.default, is_set=False)
        )

    def _consume_one(name: str) -> Any:
        nonlocal index

        if index >= len(argv):
            raise CmdError("expected another argument")

        arg = argv[index]
        if _is_flag(arg):
            raise CmdError(f"expected argument after {name}, not another flag")

        index += 1
        return arg

    def _consume_multi(name: str, *, done_with_flags: bool) -> List[Any]:
        nonlocal index

        if index >= len(argv):
            raise CmdError("expected another argument")

        r: List[str] = []
        while index < len(argv) and (done_with_flags or not _is_flag(argv[index])):
            r.append(argv[index])
            index += 1

        if not r:
            raise CmdError(f"expected argument after {name}")

        return r

    # becomes True when '--' is seen
    done_with_flags = False
    while index < len(argv):
        arg = argv[index]
        if arg == "--":
            done_with_flags = True
            index += 1
        elif not done_with_flags and _is_help_flag(arg):
            raise CmdHelpError(cmd, index)
        elif not done_with_flags and _is_version_flag(arg):
            raise CmdVersionError
        elif not done_with_flags and _is_flag(arg):
            if "=" in arg:
                arg, argvalue = arg.split("=", maxsplit=1)
            else:
                argvalue = None

            spec_and_value = flags_to_parse.get(arg)
            if spec_and_value is None:
                raise CmdError(f"unknown flag: {arg}")

            if spec_and_value.is_set:
                raise CmdError(f"flag was repeated: {arg}")

            mutex_id = flag_to_mutex_id.get(arg)
            if mutex_id is not None:
                mutex = mutexes[mutex_id]
                if mutex.satisfied is not None:
                    raise CmdError(
                        f"{mutex.satisfied} and {arg} are mutually exclusive"
                    )
                else:
                    mutex.satisfied = arg

            spec_and_value.is_set = True
            spec = spec_and_value.spec
            if spec.n == ArgCount.ZERO:
                index += 1
                if argvalue is not None:
                    if argvalue == "true":
                        spec_and_value.value = True
                    elif argvalue == "false":
                        spec_and_value.value = False
                    else:
                        raise CmdError(
                            f"flag argument must be 'true' or 'false': {arg}"
                        )
                else:
                    spec_and_value.value = True
            elif spec.n == ArgCount.ONE:
                index += 1
                if argvalue is None:
                    spec_and_value.value = _consume_one(spec.name)
                else:
                    spec_and_value.value = argvalue
            elif spec.n == ArgCount.MANY:
                index += 1
                if argvalue is None:
                    spec_and_value.value = _consume_multi(
                        spec.name, done_with_flags=False
                    )
                else:
                    spec_and_value.value = argvalue.split(",")
            else:
                impossible()
        else:
            if positionals_index >= len(positionals_to_parse):
                raise CmdError(f"extra argument: {arg}")

            spec_and_value = positionals_to_parse[positionals_index]
            spec = spec_and_value.spec
            if spec.n == ArgCount.ONE:
                index += 1
                spec_and_value.value = arg
            elif spec.n == ArgCount.MANY:
                spec_and_value.value = _consume_multi(
                    spec.name, done_with_flags=done_with_flags
                )
            else:
                impossible()

            positionals_index += 1

    if positionals_index < len(positionals_to_parse):
        missing_positionals = [
            s_and_v
            for s_and_v in positionals_to_parse[positionals_index:]
            if s_and_v.spec.required
        ]
        if len(missing_positionals) > 0:
            missing = ", ".join(s_and_v.spec.name for s_and_v in missing_positionals)
            s = "" if len(positionals_to_parse) - positionals_index == 1 else "s"
            raise CmdError(f"missing argument{s}: {missing}")

    # When checking for missing positionals/flags, we check `value is NOTHING` and not
    # `is_set` because it's OK for `is_set` to be false if a default value was set.

    missing_flags: List[str] = []
    for spec_and_value in flags_to_parse.values():
        spec = spec_and_value.spec
        if spec.required and spec_and_value.value is NOTHING:
            missing_flags.append(spec.name)

    if missing_flags:
        missing = ", ".join(sorted(missing_flags))
        s = "" if len(missing_flags) == 1 else "s"
        raise CmdError(f"missing mandatory flag{s}: {missing}")

    for mutex_state in mutexes.values():
        if mutex_state.satisfied is None and not mutex_state.optional:
            raise CmdError(
                f"exactly one of the following is required: {', '.join(mutex_state.eligible_flags)}"
            )

    args: Dict[str, Any] = {}
    kwargs: Dict[str, Any] = {}

    def apply_converter(converter: Any, x: Any) -> Any:
        if isinstance(x, list) or isinstance(x, tuple):
            return [converter(item) for item in x]
        else:
            return converter(x)

    identity = lambda x: x
    for spec_and_value in positionals_to_parse:
        converter = spec_and_value.spec.converter or identity
        if not spec_and_value.spec.required and spec_and_value.value is NOTHING:
            args[spec_and_value.spec.dest] = None
        else:
            args[spec_and_value.spec.dest] = apply_converter(
                converter, spec_and_value.value
            )

    for spec_and_value in flags_to_parse.values():
        converter = spec_and_value.spec.converter or identity
        kwargs[spec_and_value.spec.dest] = (
            apply_converter(converter, spec_and_value.value)
            if spec_and_value.value is not None
            else spec_and_value.value
        )

    return cmd._handler, ParseResult(
        args=args, kwargs=kwargs, less_logging=cmd.less_logging
    )


def _parse_group(
    group: Group, argv: List[str], index: int
) -> Tuple[Handler, ParseResult]:
    if len(group.subcmds) == 0:
        raise CmdError("group is empty")

    if index >= len(argv):
        raise CmdHelpError(group, index, "too few arguments")

    arg = argv[index]
    if _is_help_flag(arg):
        raise CmdHelpError(group, index)

    if _is_version_flag(arg):
        raise CmdVersionError

    if _is_flag(arg):
        raise CmdHelpError(group, index, f"expected subcommand, got {arg}")

    cmd_or_group = group.subcmds.get(arg)
    if cmd_or_group is None:
        raise CmdHelpError(group, index, f"unknown subcommand: {arg}")

    return _parse(cmd_or_group, argv, index + 1)


def get_help_text(cmd_or_group: Union[Command, Group], *, program: str) -> str:
    wrapper = textwrap.TextWrapper(
        initial_indent="  ",
        subsequent_indent="  ",
    )
    maybe_help = (
        [wrapper.fill(line) for line in cmd_or_group.help.splitlines()] + [""]
        if cmd_or_group.help
        else []
    )
    if isinstance(cmd_or_group, Command):
        lines = [
            f"Usage: {program} ...",
            "",
        ] + maybe_help

        before_space = 2 * " "
        before_space_minus_1 = " "
        after_space = 4 * " "

        def _fmt_help_text(spec: ArgSpec) -> str:
            return f". {spec.help}" if spec.help else ""

        table = tabular.Table()
        for spec in cmd_or_group._positionals:
            table.row([before_space, spec.name, after_space, _fmt_help_text(spec)])

        for spec in sorted(
            cmd_or_group._flags.values(),
            key=lambda spec: (not spec.required, spec.name),
        ):
            if spec.n == ArgCount.ZERO:
                modifier = ""
            elif spec.n == ArgCount.ONE:
                modifier = "ARG"
            elif spec.n == ArgCount.MANY:
                modifier = "ARGS.."
            else:
                impossible()

            help_text = _fmt_help_text(spec)
            if spec.required:
                table.row(
                    [before_space, spec.name + " " + modifier, after_space, help_text]
                )
            else:
                if modifier:
                    table.row(
                        [
                            before_space_minus_1,
                            ("[" + spec.name + " " + modifier + "]"),
                            after_space,
                            help_text,
                        ]
                    )
                else:
                    table.row(
                        [
                            before_space_minus_1,
                            "[" + spec.name + "]",
                            after_space,
                            help_text,
                        ]
                    )

        argument_lines = table.to_list(spacing=0)

        if argument_lines:
            lines += [
                "Arguments:",
                "",
            ]
            lines += argument_lines
            lines.append("")

        return "\n".join(lines)
    else:
        lines = (
            [
                f"Usage: {program} SUBCMD",
                "",
            ]
            + maybe_help
            + [
                "Subcommands:",
                "",
            ]
        )

        table = tabular.Table()
        for subcmd_name, subcmd_or_group in sorted(
            cmd_or_group.subcmds.items(), key=lambda kv: kv[0]
        ):
            if subcmd_or_group.help:
                help_text = f". {subcmd_or_group.help.splitlines()[0]}"
            else:
                help_text = ""
            table.row([f"  {subcmd_name}", "    ", help_text])

        lines.extend(table.to_list(spacing=0))

        lines.append("")
        return "\n".join(lines)


def get_help_text_recursive(
    cmd_or_group: Union[Command, Group], *, program: str
) -> str:
    match cmd_or_group:
        case Command():
            return get_help_text(cmd_or_group, program=program)
        case Group():
            group_help_text = get_help_text(cmd_or_group, program=program)
            subcmd_help = [
                get_help_text_recursive(subcmd, program=(program + " " + subcmd_name))
                for subcmd_name, subcmd in cmd_or_group.subcmds.items()
            ]

            if len(subcmd_help) == 0:
                return group_help_text
            else:
                sep = "\n\n------------\n\n"
                return group_help_text + sep + sep.join(subcmd_help)


def _is_flag(name: str) -> bool:
    return (
        name.startswith("-")
        # '-' is not a flag
        and len(name) >= 2
        # '-1' and '-1.5' are not flags
        and not _is_decimal_number(name[1:])
    )


def _is_decimal_number(s: str) -> bool:
    try:
        decimal.Decimal(s)
        return True
    except Exception:
        return False


def _is_help_flag(name: str) -> bool:
    return name in ("-h", "-help", "--help", "-?")


def _is_version_flag(name: str) -> bool:
    return name in ("-version", "--version")


@dataclass
class Mutex:
    optional: bool = False
    mutex_id: str = dataclasses.field(
        default_factory=lambda: str(uuid.uuid4()), repr=False
    )


@dataclass
class Extra:
    """
    Intended use:

        def main(myarg: Annotated[int, Extra(help="...")]):
            ...

    """

    help: str = ""
    converter: Any = None
    # Because of a flaw in this library, `converter` is applied to the arg value even if it
    # comes from `default`. This is OK in some cases, e.g., `x: int = 42` is fine; `int` will
    # just be pointlessly called on `42`. But this doesn't work:
    #
    #     duration: Annotated[timedelta, Extra(converter=parse_duration)] = timedelta(seconds=5)
    #
    # because `parse_duration` will raise if called on a `timedelta` instead of a string.
    #
    # Instead you might write:
    #
    #     duration: Annotated[...] = "5s"
    #
    # but the typechecker will complain because the string default does not match the annotated
    # type of `timedelta`. The `default` argument gives you an escape hatch:
    #
    #     duration: Annotated[timedelta, Extra(converter=parse_duration, default="5s")]
    #
    default: Any = NOTHING
    # `name` lets you use a different name for the flag and the Python parameter:
    #
    #     year_filter: Annotated[int, Extra(name="-year")]
    #
    name: str = ""
    # A command can have a single `passthrough` argument, which consumes all arguments and flags
    # on the command-line without further processing.
    #
    # This is used to collect arguments and flags to pass to another program.
    passthrough: bool = False
    # `mutex` should be passed to at least two optional flags or switches. It prevents both of the
    # flags from appearing on the same command-line.
    mutex: Optional[Mutex] = None


def _is_optional_type(type_: Any) -> bool:
    origin_type = typing.get_origin(type_)
    arg_types = typing.get_args(type_)
    return (
        (origin_type is Union or origin_type is types.UnionType)
        and len(arg_types) == 2
        and (type(None) is arg_types[1] or type(None) is arg_types[0])
    )


def _is_annotated_type(type_: Any) -> bool:
    return typing.get_origin(type_) is typing.Annotated


def _python_to_flag(s: str) -> str:
    return "-" + s.replace("_", "-")


def get_version() -> str:
    d = os.path.dirname(os.path.realpath(os.path.abspath(__file__)))
    try:
        hsh, dt = _last_commit_hash_and_datetime(repo=d)
        return f"{hsh} @ {dt}"
    except Exception:
        return "<unknown>"


# TODO(2026-02): Can this be moved to `lib/githelper`?
def _last_commit_hash_and_datetime(repo: PathLike) -> Tuple[str, datetime.datetime]:
    proc = subprocess.run(
        ["git", "-C", str(repo), "log", "-1", "--format=%h %ct"],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    )
    hsh, epoch_secs = proc.stdout.strip().split(maxsplit=1)
    return (hsh, timehelper.from_epoch_secs(int(epoch_secs)))


class CmdError(Exception):
    pass


class CmdHelpError(Exception):
    cmd_or_group: Union[Command, Group]
    index: int
    message: str

    def __init__(
        self, cmd_or_group: Union[Command, Group], index: int, message: str = ""
    ) -> None:
        super().__init__()
        self.cmd_or_group = cmd_or_group
        self.index = index
        self.message = message


class CmdVersionError(Exception):
    # not a real error, just indicates that command should print version and exit
    pass
